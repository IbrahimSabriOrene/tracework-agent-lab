"""A tiny, explicit fixture evaluation. These are not general AI benchmark claims."""

from .documents import DOCUMENTS
from .reviewer import generate_review, verify_evidence


def evaluate(profile: str, split: str = "holdout") -> dict:
    rows, true_positive, false_positive, false_negative = [], 0, 0, 0
    for doc in DOCUMENTS:
        if doc["split"] != split:
            continue
        accepted, rejected = verify_evidence(doc["text"], generate_review(doc["text"], profile))
        actual = {item["rule"] for item in accepted}
        expected = set(doc["expected"])
        true_positive += len(actual & expected)
        false_positive += len(actual - expected)
        false_negative += len(expected - actual)
        rows.append(
            {
                "id": doc["id"],
                "expected": sorted(expected),
                "actual": sorted(actual),
                "passed": actual == expected and not rejected,
            }
        )
    precision = (
        true_positive / (true_positive + false_positive)
        if (true_positive + false_positive)
        else 1.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if (true_positive + false_negative)
        else 1.0
    )
    return {
        "profile": profile,
        "split": split,
        "documents": len(rows),
        "rows": rows,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "note": "Deterministic synthetic fixtures; not a statistical model-quality estimate.",
    }
