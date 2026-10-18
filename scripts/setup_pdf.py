"""Prepare the optional local CPU OCR worker and models; no document leaves this machine."""

import os
import shutil
import subprocess
from pathlib import Path

from tracework.pdf import MINERU_VERSION, ROOT, mineru_environment, worker_python


def main():
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("Install uv first: https://docs.astral.sh/uv/")
    python = worker_python()
    if not python.is_file():
        subprocess.run([uv, "venv", "--python", "3.12", str(ROOT / ".mineru")], check=True)
    subprocess.run(
        [
            uv,
            "pip",
            "install",
            "--system-certs",
            "--python",
            str(python),
            f"mineru=={MINERU_VERSION}",
        ],
        check=True,
    )
    data_dir = Path(os.getenv("TRACEWORK_DATA_DIR", ".data")).resolve()
    env = mineru_environment(data_dir, download=True)
    executable = python.parent / ("mineru-kit.exe" if os.name == "nt" else "mineru-kit")
    subprocess.run(
        [str(executable), "models", "download", "--tier", "basic", "--small-backend", "onnx"],
        env=env,
        check=True,
    )
    subprocess.run(
        [str(executable), "models", "verify", "--tier", "basic", "--small-backend", "onnx"],
        env=mineru_environment(data_dir),
        check=True,
    )
    ready = data_dir / "mineru/models/.tracework-ready"
    ready.write_text(MINERU_VERSION, "utf-8")
    print("Local MinerU Basic/ONNX is prepared. Start Tracework and choose Import PDF.")


if __name__ == "__main__":
    main()
