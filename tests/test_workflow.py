import json

import pytest
from fastapi.testclient import TestClient

from tracework.api import create_app
from tracework.documents import get_document
from tracework.evaluation import evaluate
from tracework.reviewer import Finding, Review, verify_evidence
from tracework.workflow import Lab


def test_checkpoint_survives_restart_and_report_publishes_once(tmp_path):
    doc = get_document("atlas-launch")
    first = Lab(tmp_path)
    pending = first.start(doc["title"], doc["text"], "evidence")
    assert pending["status"] == "awaiting_review"
    assert pending["can_decide"]
    with pytest.raises(KeyError):
        first.report(pending["run_id"])
    first.close()
    restarted = Lab(tmp_path)
    try:
        published = restarted.decide(pending["run_id"], True, "Checked against the source.")
        assert published["status"] == "published"
        assert len(published["findings"]) == 3
        assert restarted.report(pending["run_id"])["reviewer_note"] == "Checked against the source."
        with pytest.raises(ValueError):
            restarted.decide(pending["run_id"], True, "Duplicate")
        assert restarted.connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1
    finally:
        restarted.close()


def test_embedded_instruction_cannot_approve_and_human_can_reject(tmp_path):
    lab = Lab(tmp_path)
    try:
        doc = get_document("cedar-handoff")
        state = lab.start(doc["title"], doc["text"], "evidence")
        assert "embedded-instruction" in {item["rule"] for item in state["findings"]}
        assert state["can_decide"] and "approved" not in state
        assert lab.decide(state["run_id"], False, "Needs revision.")["status"] == "rejected"
        assert lab.connection.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
    finally:
        lab.close()


def test_unsupported_quotes_and_duplicates_are_withheld():
    good = Finding(
        rule="owner",
        title="Missing owner",
        severity="medium",
        quote="Owner: TBD",
        line=1,
        suggestion="Assign an owner.",
    )
    invented = good.model_copy(update={"quote": "Invented evidence", "line": 2})
    accepted, rejected = verify_evidence(
        "Owner: TBD\nTarget date: 2026-11-18",
        Review(summary="A source-backed review.", findings=[good, good, invented]),
    )
    assert len(accepted) == 1
    assert len(rejected) == 2


def test_holdout_is_explicit_and_clean_control_has_no_false_positives():
    baseline, improved = evaluate("baseline"), evaluate("evidence")
    assert baseline["documents"] == improved["documents"] == 4
    assert baseline["recall"] == 0.5
    assert improved["recall"] == improved["precision"] == 1
    assert improved["false_positive"] == 0
    assert all(row["id"] not in {"atlas-launch", "cedar-handoff"} for row in improved["rows"])


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as connection:
        yield connection


def test_api_review_decision_and_export(client):
    doc = get_document("atlas-launch")
    response = client.post(
        "/api/reviews", json={"title": doc["title"], "document": doc["text"], "profile": "evidence"}
    )
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    assert client.get(f"/api/reviews/{run_id}/report").status_code == 404
    assert (
        client.post(f"/api/reviews/{run_id}/decision", json={"approved": "yes"}).status_code == 422
    )
    assert (
        client.post(f"/api/reviews/{run_id}/decision", json={"approved": True}).status_code == 200
    )
    report = client.get(f"/api/reviews/{run_id}/report").json()
    assert len(report["document_sha256"]) == 64
    assert (
        client.post(f"/api/reviews/{run_id}/decision", json={"approved": True}).status_code == 409
    )
    assert client.get("/api/runs").json()[0]["status"] == "published"


def test_api_validates_input_and_blocks_browser_cross_origin_mutations(client):
    assert client.post("/api/reviews", json={"title": "x", "document": "short"}).status_code == 422
    doc = get_document("atlas-launch")
    payload = {"title": "Test", "document": doc["text"], "profile": "unknown"}
    assert client.post("/api/reviews", json=payload).status_code == 409
    assert (
        client.post(
            "/api/reviews", json=payload, headers={"Origin": "https://unrelated.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/reviews/not-an-id").status_code == 422
    assert client.get("/api/documents").status_code == 200
    assert "expected" not in json.dumps(client.get("/api/documents").json())
    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"
