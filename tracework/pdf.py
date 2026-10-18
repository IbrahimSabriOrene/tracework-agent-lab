"""Bounded local PDF import through an isolated, pinned MinerU environment."""

import hashlib
import io
import json
import os
import subprocess
import tempfile
import threading
import uuid
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

ROOT = Path(__file__).resolve().parent.parent
MINERU_VERSION = "4.0.12"
MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_PDF_PAGES = 5
MAX_TEXT = 20000


class PdfError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


def worker_python() -> Path:
    configured = os.getenv("TRACEWORK_MINERU_PYTHON")
    if configured:
        return Path(configured).expanduser().resolve()
    return ROOT / ".mineru" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def mineru_environment(data_dir: Path, *, download: bool = False) -> dict[str, str]:
    """Keep configuration separate from the user's global MinerU configuration."""
    home = (data_dir / "mineru").resolve()
    home.mkdir(parents=True, exist_ok=True)
    config = home / "config.yaml"
    config.write_text(
        json.dumps(
            {
                "model": {
                    "base_dir": str(home / "models"),
                    "source": "local",
                    "small_backend": "onnx",
                },
                "llm_aided": {
                    "features": {"title_leveling": False, "cross_page_table_cell_merge": False}
                },
            }
        ),
        "utf-8",
    )
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("MINERU_") or key in {"HF_HUB_OFFLINE", "MODELSCOPE_OFFLINE"}:
            env.pop(key)
    env.update(
        MINERU_HOME=str(home),
        MINERU_CONFIG=str(config),
        MINERU_MODEL_SOURCE="auto" if download else "local",
        HF_HUB_OFFLINE="0" if download else "1",
        MODELSCOPE_OFFLINE="0" if download else "1",
        MINERU_TABLE_DEVICE="cpu",
        PYTHONUTF8="1",
    )
    return env


class PdfImporter:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.resolve()
        self.imports = self.data_dir / "pdf-imports"
        self.imports.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()

    def capabilities(self) -> dict:
        installed = worker_python().is_file()
        models = self.data_dir / "mineru" / "models"
        return {
            "installed": installed,
            "models_prepared": (models / ".tracework-ready").is_file(),
            "available": installed and (models / ".tracework-ready").is_file(),
            "parser": "MinerU",
            "version": MINERU_VERSION,
            "tier": "basic",
            "local_only": True,
            "max_bytes": MAX_PDF_BYTES,
            "max_pages": MAX_PDF_PAGES,
        }

    def extract(self, payload: bytes, filename: str) -> dict:
        if len(payload) > MAX_PDF_BYTES:
            raise PdfError("PDF exceeds the 5 MiB limit.", 413)
        name = filename.replace("\\", "/").split("/")[-1][:150]
        if not name.lower().endswith(".pdf") or not payload.startswith(b"%PDF-"):
            raise PdfError("Choose a valid PDF file.")
        try:
            reader = PdfReader(io.BytesIO(payload), strict=False)
            if reader.is_encrypted:
                raise PdfError("Encrypted PDFs are not supported. Use an unlocked copy.")
            page_count = len(reader.pages)
            if not 1 <= page_count <= MAX_PDF_PAGES:
                raise PdfError("Choose a PDF with 1 to 5 pages; no pages are silently skipped.")
            for page in reader.pages:
                if float(page.mediabox.width) * float(page.mediabox.height) > 4000000:
                    raise PdfError("PDF page dimensions exceed the local demo limit.")
        except (PdfReadError, ValueError, KeyError, TypeError, OverflowError) as exc:
            raise PdfError("The PDF is malformed or cannot be read.") from exc
        if not self.capabilities()["available"]:
            raise PdfError("Set up local MinerU first: uv run python scripts/setup_pdf.py", 503)
        if not self.lock.acquire(blocking=False):
            raise PdfError("Another PDF is being extracted. Try again when it finishes.", 409)
        try:
            env = mineru_environment(self.data_dir)
            with tempfile.TemporaryDirectory(prefix="pdf-", dir=self.data_dir) as directory:
                work = Path(directory)
                source, result = work / "source.pdf", work / "result.json"
                source.write_bytes(payload)
                with (work / "worker.log").open("wb") as log:
                    try:
                        process = subprocess.run(
                            [
                                str(worker_python()),
                                str(ROOT / "scripts/mineru_worker.py"),
                                str(source),
                                str(result),
                            ],
                            cwd=work,
                            env=env,
                            stdout=log,
                            stderr=subprocess.STDOUT,
                            timeout=600,
                            check=False,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        )
                    except subprocess.TimeoutExpired as exc:
                        raise PdfError(
                            "Local MinerU timed out after 10 minutes. Try a smaller PDF.", 504
                        ) from exc
                if process.returncode or not result.is_file():
                    # Keep bounded local diagnostics; never expose raw worker output in the UI.
                    with (work / "worker.log").open("rb") as log:
                        log.seek(max(0, log.seek(0, 2) - 16000))
                        (self.data_dir / "pdf-worker.log").write_bytes(log.read(16000))
                    raise PdfError(
                        "Local MinerU failed. Check .data/pdf-worker.log and the PDF setup guide.",
                        502,
                    )
                if result.stat().st_size > 4 * MAX_TEXT + 4096:
                    raise PdfError("Extracted text exceeds 20,000 characters. Split the PDF.")
                output = json.loads(result.read_text("utf-8"))
                document = output["document"].strip()
                if not 20 <= len(document) <= MAX_TEXT:
                    raise PdfError(
                        "Extracted text must contain 20–20,000 characters. Split or check the PDF."
                    )
                if output["version"] != MINERU_VERSION or output["pages"] != page_count:
                    raise PdfError(
                        "MinerU returned an unsupported version or incomplete page result.", 502
                    )
                import_id = str(uuid.uuid4())
                metadata = {
                    "kind": "pdf",
                    "filename": name,
                    "pdf_sha256": hashlib.sha256(payload).hexdigest(),
                    "pages": page_count,
                    "parser": "MinerU",
                    "parser_version": output["version"],
                    "tier": "basic",
                    "local_only": True,
                    "extracted_text_sha256": hashlib.sha256(document.encode()).hexdigest(),
                }
                artifact = {
                    "import_id": import_id,
                    "title": Path(name).stem or "Imported PDF",
                    "document": document,
                    "source": metadata,
                }
                (self.imports / f"{import_id}.json").write_text(json.dumps(artifact), "utf-8")
                return artifact
        finally:
            self.lock.release()

    def source(self, import_id: str, document: str) -> dict:
        import_id = str(uuid.UUID(import_id))
        path = self.imports / f"{import_id}.json"
        if not path.is_file():
            raise PdfError("PDF import not found. Extract the PDF again.", 404)
        source = json.loads(path.read_text("utf-8"))["source"]
        source["import_id"] = import_id
        source["text_edited"] = (
            source["extracted_text_sha256"] != hashlib.sha256(document.encode()).hexdigest()
        )
        return source
