import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from tracework.api import create_app
from tracework.pdf import MAX_PDF_BYTES, MINERU_VERSION

TEXT = "# Imported brief\nContent owner: TBD.\nThe review happens next Friday.\n"


def pdf_bytes(pages=1, encrypted=False):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    if encrypted:
        writer.encrypt("test-only-password")
    stream = io.BytesIO()
    writer.write(stream)
    return stream.getvalue()


@pytest.fixture
def prepared_pdf(tmp_path, monkeypatch):
    worker = tmp_path / "python"
    worker.touch()
    monkeypatch.setenv("TRACEWORK_MINERU_PYTHON", str(worker))
    monkeypatch.setenv("MINERU_API_URL", "https://must-not-be-used.invalid")
    ready = tmp_path / "mineru/models/.tracework-ready"
    ready.parent.mkdir(parents=True)
    ready.write_text(MINERU_VERSION)
    calls = []

    def run(args, **kwargs):
        calls.append((args, kwargs))
        assert kwargs["env"]["MINERU_MODEL_SOURCE"] == "local"
        assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
        assert "MINERU_API_URL" not in kwargs["env"]
        Path(args[-1]).write_text(
            json.dumps({"version": MINERU_VERSION, "pages": 1, "document": TEXT}), "utf-8"
        )
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("tracework.pdf.subprocess.run", run)
    return tmp_path, calls


def test_pdf_import_review_and_restart_preserve_provenance(prepared_pdf):
    root, calls = prepared_pdf
    with TestClient(create_app(root)) as client:
        assert client.get("/api/health").json()["pdf"]["available"]
        response = client.post(
            "/api/pdf/extract", files={"file": ("../../brief.pdf", pdf_bytes(), "application/pdf")}
        )
        assert response.status_code == 201
        imported = response.json()
        assert imported["source"]["filename"] == "brief.pdf"
        assert len(imported["source"]["pdf_sha256"]) == 64
        assert client.get("/api/runs").json() == []  # Extraction never starts or approves a review.
        review = client.post(
            "/api/reviews",
            json={
                "title": imported["title"],
                "document": TEXT + "Human edit.\n",
                "pdf_import_id": imported["import_id"],
            },
        ).json()
        assert review["status"] == "awaiting_review"
        assert review["source"]["text_edited"]
        assert len(review["findings"]) == 2
        run_id = review["run_id"]
    with TestClient(create_app(root)) as restarted:
        assert restarted.get(f"/api/reviews/{run_id}").json()["source"]["local_only"]
        assert (
            restarted.post(f"/api/reviews/{run_id}/decision", json={"approved": True}).status_code
            == 200
        )
        report = restarted.get(f"/api/reviews/{run_id}/report").json()
        assert report["source"]["parser_version"] == MINERU_VERSION
        assert report["source"]["import_id"] == imported["import_id"]
    assert len(calls) == 1
    assert not list(root.glob("pdf-*/*.pdf"))  # Uploaded bytes are temporary.


def test_pdf_rejects_invalid_encrypted_large_and_too_many_pages(prepared_pdf):
    root, calls = prepared_pdf
    with TestClient(create_app(root)) as client:
        for payload in (b"not a PDF", b"%PDF-broken", pdf_bytes(6), pdf_bytes(encrypted=True)):
            response = client.post("/api/pdf/extract", files={"file": ("sample.pdf", payload)})
            assert response.status_code == 422
        assert (
            client.post(
                "/api/pdf/extract", files={"file": ("huge.pdf", b"%PDF-" + b"x" * MAX_PDF_BYTES)}
            ).status_code
            == 413
        )
        assert (
            client.post("/api/pdf/extract", files={"file": ("other.txt", pdf_bytes())}).status_code
            == 422
        )
        assert (
            client.post(
                "/api/pdf/extract",
                files={"file": ("sample.pdf", pdf_bytes())},
                headers={"Origin": "https://unrelated.example"},
            ).status_code
            == 403
        )
    assert not calls


def test_pdf_setup_is_explicit_and_does_not_fall_back(tmp_path, monkeypatch):
    monkeypatch.setenv("TRACEWORK_MINERU_PYTHON", str(tmp_path / "missing-python"))
    with TestClient(create_app(tmp_path)) as client:
        assert not client.get("/api/health").json()["pdf"]["available"]
        result = client.post("/api/pdf/extract", files={"file": ("sample.pdf", pdf_bytes())})
        assert result.status_code == 503
        assert client.get("/api/runs").json() == []
        assert (
            client.post(
                "/api/reviews",
                json={
                    "title": "Unknown import",
                    "document": TEXT,
                    "pdf_import_id": "00000000-0000-0000-0000-000000000000",
                },
            ).status_code
            == 404
        )


def test_pdf_timeout_cleans_up_and_releases_single_worker(prepared_pdf, monkeypatch):
    root, _ = prepared_pdf

    def timeout(args, **kwargs):
        raise subprocess.TimeoutExpired(args, kwargs["timeout"])

    monkeypatch.setattr("tracework.pdf.subprocess.run", timeout)
    with TestClient(create_app(root)) as client:
        for _ in range(2):
            assert (
                client.post(
                    "/api/pdf/extract", files={"file": ("sample.pdf", pdf_bytes())}
                ).status_code
                == 504
            )
        assert not list(root.glob("pdf-*/*.pdf"))
        client.app.state.pdf.lock.acquire()
        try:
            assert (
                client.post(
                    "/api/pdf/extract", files={"file": ("sample.pdf", pdf_bytes())}
                ).status_code
                == 409
            )
        finally:
            client.app.state.pdf.lock.release()


def test_pdf_unicode_limit_and_incomplete_worker_output(prepared_pdf, monkeypatch):
    root, _ = prepared_pdf
    output = {"version": MINERU_VERSION, "pages": 1, "document": "ü" * 20000}

    def run(args, **kwargs):
        Path(args[-1]).write_text(json.dumps(output, ensure_ascii=False), "utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("tracework.pdf.subprocess.run", run)
    with TestClient(create_app(root)) as client:
        for update, expected in [
            ({}, 201),
            ({"document": "ü" * 20001}, 422),
            ({"document": TEXT, "pages": 2}, 502),
            ({"pages": 1, "version": "unsupported"}, 502),
        ]:
            output.update(update)
            response = client.post("/api/pdf/extract", files={"file": ("sample.pdf", pdf_bytes())})
            assert response.status_code == expected, response.text
