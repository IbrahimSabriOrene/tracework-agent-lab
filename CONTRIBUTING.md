# Contributing

Start with a small issue or pull request describing a reproducible behavior. Keep the distinction
between offline fixtures, optional model review, and static browser playback explicit.

```bash
uv sync --locked
uv run ruff check tracework tests
uv run ruff format --check tracework tests
uv run pytest -q
```

Run the full suite on Linux or Docker; Windows cannot execute the upstream POSIX scheduler.
Add behavioral tests for changes to checkpoint/resume, publication, evidence, and edit boundaries.
Avoid tests that only duplicate implementation details.

Keep fixtures synthetic. Do not include credentials, real customer documents, proprietary code,
provider response logs with personal data, or unrelated project assets. Add new review rules and
evaluation cases together, and explain how rule-level metrics should be interpreted.

For upstream Harness² changes, update the pinned commit deliberately and verify both recursion
modes. Do not add a workaround that disables locking or allows arbitrary generated code execution.
