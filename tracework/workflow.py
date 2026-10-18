"""A real LangGraph workflow with durable interrupt/resume and idempotent publication."""

import hashlib
import json
import operator
import sqlite3
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .reviewer import PROFILES, Review, generate_review, verify_evidence


class ReviewState(TypedDict, total=False):
    run_id: str
    title: str
    document: str
    profile: str
    engine: str
    status: str
    raw_review: dict
    findings: list[dict]
    rejected: list[dict]
    approved: bool
    reviewer_note: str
    report_id: str
    trace: Annotated[list[dict], operator.add]


def event(step: str, detail: str) -> dict:
    return {"step": step, "detail": detail, "at": datetime.now(UTC).isoformat()}


def review_graph(checkpointer, publish):
    def read_source(state):
        return {
            "status": "reviewing",
            "trace": [
                event(
                    "Read source",
                    f"Loaded {len(state['document'].splitlines())} lines as untrusted data.",
                )
            ],
        }

    def review(state):
        result = generate_review(state["document"], state["profile"], state["engine"])
        return {
            "raw_review": result.model_dump(),
            "trace": [
                event(
                    "Review document",
                    f"{state['engine']} reviewer used {state['profile']} harness.",
                )
            ],
        }

    def evidence(state):
        accepted, rejected = verify_evidence(
            state["document"], Review.model_validate(state["raw_review"])
        )
        return {
            "findings": accepted,
            "rejected": rejected,
            "status": "awaiting_review",
            "trace": [
                event(
                    "Verify evidence",
                    f"{len(accepted)} accepted; "
                    f"{len(rejected)} unsupported or duplicate findings withheld.",
                )
            ],
        }

    def approval(state):
        decision = interrupt(
            {
                "kind": "review_approval",
                "run_id": state["run_id"],
                "message": "Approve publication of this review report?",
                "finding_count": len(state["findings"]),
            }
        )
        if not isinstance(decision, dict) or type(decision.get("approved")) is not bool:
            raise ValueError("Approval requires an explicit boolean decision.")
        return {
            "approved": decision["approved"],
            "reviewer_note": decision.get("note", ""),
            "status": "approved" if decision["approved"] else "rejected",
            "trace": [
                event(
                    "Human decision",
                    "Approved report publication."
                    if decision["approved"]
                    else "Report publication rejected.",
                )
            ],
        }

    def publication(state):
        report_id = publish(state)
        return {
            "report_id": report_id,
            "status": "published",
            "trace": [event("Publish report", "Saved one local report; no external delivery.")],
        }

    builder = StateGraph(ReviewState)
    for name, node in [
        ("read", read_source),
        ("review", review),
        ("verify", evidence),
        ("approval", approval),
        ("publish", publication),
    ]:
        builder.add_node(name, node)
    builder.add_edge(START, "read")
    builder.add_edge("read", "review")
    builder.add_edge("review", "verify")
    builder.add_edge("verify", "approval")
    builder.add_conditional_edges("approval", lambda s: "publish" if s["approved"] else END)
    builder.add_edge("publish", END)
    return builder.compile(checkpointer=checkpointer)


class Lab:
    def __init__(self, data_dir: Path, engine: str = "offline"):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine
        self.connection = sqlite3.connect(data_dir / "tracework.sqlite", check_same_thread=False)
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.executescript(
            "CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,title TEXT,created_at TEXT);"
            "CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY,run_id TEXT UNIQUE,body TEXT);"
        )
        self.connection.commit()
        # ponytail: one-process demo lock; use transactional claims before multi-worker hosting.
        self.lock = threading.RLock()
        self.checkpoint_connection = sqlite3.connect(
            data_dir / "checkpoints.sqlite", check_same_thread=False
        )
        self.checkpointer = SqliteSaver(self.checkpoint_connection)
        self.graph = review_graph(self.checkpointer, self._publish)

    def _publish(self, state):
        report_id = "report-" + state["run_id"]
        payload = {
            k: state.get(k)
            for k in [
                "run_id",
                "title",
                "profile",
                "engine",
                "findings",
                "rejected",
                "reviewer_note",
            ]
        }
        payload["document_sha256"] = hashlib.sha256(state["document"].encode()).hexdigest()
        payload["harness_version"] = PROFILES[state["profile"]]["version"]
        payload["prompt_sha256"] = hashlib.sha256(
            PROFILES[state["profile"]]["prompt"].encode()
        ).hexdigest()
        payload["summary"] = state["raw_review"]["summary"]
        self.connection.execute(
            "INSERT OR IGNORE INTO reports VALUES (?,?,?)",
            (report_id, state["run_id"], json.dumps(payload)),
        )
        self.connection.commit()
        return report_id

    @staticmethod
    def config(run_id):
        return {"configurable": {"thread_id": run_id}}

    def start(self, title: str, document: str, profile: str) -> dict:
        if profile not in PROFILES:
            raise ValueError("Unknown harness profile.")
        run_id = str(uuid.uuid4())
        with self.lock:
            self.connection.execute(
                "INSERT INTO runs VALUES (?,?,?)", (run_id, title, datetime.now(UTC).isoformat())
            )
            self.connection.commit()
            self.graph.invoke(
                {
                    "run_id": run_id,
                    "title": title,
                    "document": document,
                    "profile": profile,
                    "engine": self.engine,
                    "trace": [],
                },
                self.config(run_id),
            )
            return self.get(run_id)

    def get(self, run_id: str) -> dict:
        with self.lock:
            if not self.connection.execute("SELECT 1 FROM runs WHERE id=?", (run_id,)).fetchone():
                raise KeyError(run_id)
            snapshot = self.graph.get_state(self.config(run_id))
            state = dict(snapshot.values)
            state["can_decide"] = bool(snapshot.next and state.get("status") == "awaiting_review")
            state["profile_info"] = PROFILES.get(state.get("profile"), {})
            return state

    def decide(self, run_id: str, approved: bool, note: str) -> dict:
        with self.lock:
            current = self.get(run_id)
            if not current["can_decide"]:
                raise ValueError("This run is not waiting for a decision.")
            self.graph.invoke(
                Command(resume={"approved": approved, "note": note}), self.config(run_id)
            )
            return self.get(run_id)

    def list_runs(self) -> list[dict]:
        with self.lock:
            rows = self.connection.execute(
                "SELECT id,title,created_at FROM runs ORDER BY created_at DESC LIMIT 30"
            ).fetchall()
            return [
                {
                    "id": row[0],
                    "title": row[1],
                    "created_at": row[2],
                    "status": self.get(row[0]).get("status", "interrupted"),
                }
                for row in rows
            ]

    def report(self, run_id: str) -> dict:
        with self.lock:
            row = self.connection.execute("SELECT body FROM reports WHERE run_id=?", (run_id,))
            result = row.fetchone()
            if not result:
                raise KeyError(run_id)
            return json.loads(result[0])

    def close(self):
        self.checkpoint_connection.close()
        self.connection.close()
