"""Generate a clearly labelled static walkthrough from actual local LangGraph executions."""

import json
import tempfile
from pathlib import Path

from .documents import public_documents
from .evaluation import evaluate
from .harness_adapter import run_experiment
from .reviewer import PROFILES
from .workflow import Lab


def export_replay():
    recordings = {}
    with tempfile.TemporaryDirectory() as temporary:
        lab = Lab(Path(temporary))
        try:
            for doc in public_documents():
                for profile in PROFILES:
                    state = lab.start(doc["title"], doc["text"], profile)
                    # Browser playback uses explicit local state transitions; no live approval API.
                    for entry in state["trace"]:
                        entry.pop("at", None)
                    state["run_id"] = f"replay-{doc['id']}-{profile}"
                    recordings[f"{doc['id']}:{profile}"] = state
        finally:
            lab.close()
        experiment = run_experiment(Path(temporary) / "experiment")
    payload = {
        "mode": "replay",
        "generated_by": "Actual offline LangGraph runs",
        "documents": public_documents(),
        "profiles": PROFILES,
        "recordings": recordings,
        "evaluation": {key: evaluate(key) for key in PROFILES},
    }
    payload["experiment"] = experiment
    target = Path(__file__).resolve().parent.parent / "web" / "replay.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(recordings)} real graph recordings to {target.name}.")
