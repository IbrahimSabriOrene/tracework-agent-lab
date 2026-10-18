# Experiment methodology

## Research question

Can a narrow document-review harness be expanded while keeping source evidence checks and human
publication approval outside its editable surface? Tracework demonstrates the integration mechanics
with a predefined change. It does not claim to answer that question for arbitrary real documents.

## What changes

- Baseline: explicit unresolved owner, acceptance, and rollback fields.
- Evidence-aware: those cues plus relative dates, pending dependencies, and embedded commands.
- The prompt identifies an allowlisted profile. In offline mode, that profile selects transparent rules.
- `ScriptedEditor` supplies the predefined expansion and evidence-coverage selection heuristic.

Real Harness² core code runs the reference/probe/composition executions and reflection library.
The experiment's language-model cost is zero because neither the reviewer nor editor calls a model.
It is not zero-compute, and no provider cost estimate is implied for a model-backed configuration.

## Partitions

Two development documents enter the adaptation stream: `atlas-launch` and `cedar-handoff`.
Four held-out fixtures are evaluated independently: `lumen-release`, `harbor-proposal`,
`willow-injection`, and `maple-ready`.

Expected rule labels are stored for reproducible evaluation but are not copied into adaptation
source directories or proposer/selector contexts. The dataset is public and intentionally small;
this is a data-flow separation, not a claim that these fixtures resist benchmark contamination.
An LLM optimizer should use newly authored, blinded, larger holdout sets before any quality claim.

## Metrics

We compare sets of rule-family identifiers per document. True positives are the intersection with
expected labels; false positives are unexpected labels; false negatives are missed labels.
Precision and recall are micro-aggregated across the four documents. Matching a rule family does not
measure explanation quality, full issue localization, business significance, or human agreement.

The clean control tests over-reporting. The selector's preference for more source-backed observations
is only a scripted heuristic; the independent false-positive check is essential. An exact quote
proves the text exists, not that a finding's interpretation follows from it.

## Reproduce and inspect

```bash
uv run tracework experiment --mode sequential --budget 1 --output .data/seq
uv run tracework experiment --mode parallel --budget 1 --output .data/par
uv run tracework evaluate
```

Use a new output directory when changing task data or configuration. The upstream execution records
have their own resume/fingerprint semantics. On Windows, run these commands in Docker or WSL.

Inspect `experiment.json` for task completion, actual LangGraph execution IDs, selected profiles,
editor-call counts, and holdout metrics. Under the same root, inspect review artifacts, source-backed
trajectories, candidate harness text, selections, and the persisted reflection library.

Both parallel and sequential recursion are tested. The budget is deliberately capped at 2 in this
demo. Candidate runs stop before publication and cannot change review verification or approval.

## Extending to a model-backed research experiment

The optional Ollama reviewer is available for interactive document review only. Replacing the
scripted optimizer is a separate change: implement model-backed proposer, composition, selection,
and reflection sessions while retaining edit-surface validation and isolated execution. Add model
IDs, prompt hashes, sampling settings, token usage, cost, and independent human/evaluation judgments.
Run several seeds on a larger dataset. Report failures as failures rather than favorable zeros.

This repository intentionally does not present a scripted candidate expansion as autonomous learning.
