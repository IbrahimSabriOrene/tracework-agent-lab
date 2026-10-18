import os

import pytest

from tracework.harness_adapter import DocumentAdapter, run_experiment


@pytest.mark.parametrize("mode", ["sequential", "parallel"])
@pytest.mark.skipif(os.name == "nt", reason="The upstream scheduler uses POSIX fcntl locks.")
def test_real_upstream_recursion_executes_langgraph_without_publication(tmp_path, mode):
    result = run_experiment(tmp_path, mode)
    assert result["outcome"]["done"] == 2
    assert result["outcome"]["failed"] == 0
    assert {row["profile"] for row in result["executions"]} == {"baseline", "evidence"}
    assert len(result["executions"]) >= 6
    assert result["editor_calls"] > 0
    lessons = list((tmp_path / "library").rglob("EXPERIENCE.md"))
    assert lessons and "lesson" in lessons[0].read_text().lower()
    assert not list(tmp_path.rglob("tracework.sqlite"))
    assert not {row["task"] for row in result["executions"]} & {
        "lumen-release",
        "harbor-proposal",
        "willow-injection",
        "maple-ready",
    }


def test_experiment_surface_rejects_code_and_unknown_profiles(tmp_path):
    adapter = DocumentAdapter(tmp_path)
    with pytest.raises(ValueError):
        adapter.validate_tree(
            {
                "systemprompt.md": "Harness profile: evidence",
                "scripts/execute.py": "print('not permitted')",
            }
        )
    with pytest.raises(ValueError):
        adapter.validate_tree({"systemprompt.md": "Harness profile: unrestricted"})
