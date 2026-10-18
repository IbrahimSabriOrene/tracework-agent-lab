# Architecture

Tracework separates review generation, workflow orchestration, enforceable evidence checks,
human decisions, and isolated harness experiments. The default engine is deterministic.

![Local review, isolated Harness² improvement, and hosted replay](images/architecture.png)

**How to read this:** the upper lane is the local application; the middle lane is an isolated
experiment using a custom adapter; the lower lane is the hosted recording player. Experiment
results are artifacts for inspection, not automatic runtime configuration changes. The graphic
was generated with image_gen and checked against the implementation; the
[generation prompt](images/architecture-prompt.txt) is included for reproducibility.

New to the project? Follow the [step-by-step tests](testing.md) or
[Türkçe test rehberi](testing.tr.md) before reading the implementation details below.

## Online review path

Optional PDF ingestion happens **before** the review graph:

`PDF upload → bounded validation → local MinerU Basic/ONNX worker → inspect/edit extracted text → start review`

MinerU 4.0.12 runs in a separate Python environment. Runtime configuration selects local models,
CPU ONNX, and no LLM-assisted postprocessing or remote parser. Setup explicitly downloads models;
the hosted static site cannot perform extraction. The bounded worker call is not an agent tool.

Extraction stores a local JSON artifact but does not start or approve a review. The API resolves
the artifact's UUID to trusted provenance when starting the graph. Graph state and the published
report retain the original PDF hash, page count, parser version, initial text hash, and whether
the reviewed text was edited. The uploaded PDF's temporary server copy is removed after parsing.
The existing diagram begins at the resulting source text. See [PDF setup and data handling](pdf.md).

Exact-quote verification applies to extracted/corrected text, not original PDF pixels. Human review
must also assess OCR accuracy. Page-local PDF coordinates are not claimed by text-line citations.

`read → review → verify → approval → publish / end`

1. **Read:** store the document in graph state as untrusted text. No document command is executed.
2. **Review:** invoke the selected deterministic fixture profile or optional local Ollama model.
3. **Verify:** parse typed findings, enforce exact source-line quotes, and withhold duplicates.
4. **Approval:** `interrupt()` suspends the graph. Approval is supplied only through an explicit API
   decision, never extracted from document content or model output.
5. **Publish:** write one local JSON report with a deterministic `report-<run_id>` identifier.

The response before approval includes the draft findings and an execution trace. Approval means
publication of that review artifact, not approval of the source document or any implied business action.

## Persistent state and replay

`checkpoints.sqlite` belongs to LangGraph's `SqliteSaver`. `tracework.sqlite` contains the local
run index and published reports. Separate connections avoid mixing graph checkpoint transactions
with report writes. A single application lock serializes review mutations in this teaching demo.

After restart, the application reconstructs the graph with the same durable checkpointer and
thread identifier. The node containing `interrupt()` restarts when resumed. Publication therefore
uses a unique run key and insert-if-absent behavior. A repeated API decision is rejected once the
graph no longer waits for approval.

An application crash between the report insert and the following graph checkpoint can replay
the publish node. The database uniqueness key returns the existing report identity instead of
creating another local artifact. External delivery is not implemented. Do not infer a general
exactly-once guarantee from checkpointing.

## Harness² integration seam

Pinned source: `google-research/harness2@1cfe254e8d25b15f37048c3730134686abe60335`.

`DocumentAdapter` implements the upstream task, source, execution, artifact, trajectory, validation,
and scoring contracts. `LangGraphSurface` reuses the upstream text-tree schema, while the adapter's
`execute` method launches a fresh LangGraph in-memory execution. No OpenCode/Codex subprocess runs.

The experiment invokes the upstream `run_domain`, which performs real reference executions,
Propose–Probe–Compose recursion, selection, and reflection. The `ScriptedEditor` is deliberately
deterministic: it changes only prompt text selecting a predefined review profile. It is not a
model-backed optimizer and it does not synthesize novel Python code.

Only the development task stream enters adaptation. Every probe has a fresh graph/checkpointer.
The graph stops at the human interrupt; publication in the experiment is unavailable. The adapter's
tree validation rejects scripts, plugins, extra files, nonempty secondary text components, and
unknown profile identifiers. Model-independent evidence verification cannot be edited by a candidate.

The upstream scheduler uses POSIX file locking for experiment summaries. Native Windows review is
supported; full adaptation and export run in Docker, Linux, or WSL. There is no unsafe locking shim.

## Browser walkthrough

GitHub Pages cannot run the Python backend. `tracework export-replay` generates `web/replay.json`
from actual local graph executions and an actual scripted adaptation run. The same frontend first
checks for the local API. If it is absent, the app clearly labels itself as interactive replay.

In replay mode, document and profile selection choose a recorded draft, source inspection is fully
interactive, and approve/reject only mutate temporary browser state. Custom-text review is disabled.
Downloading produces a replay-labelled artifact. There are no hidden model calls or uploads.

## Optional model boundary

Ollama is configured on the server, not through browser-supplied URLs. The source document is sent
as one data value; the model returns a schema-constrained review. It has no shell, filesystem,
network, or publication tools. Exact quotes are validated independently. Semantic accuracy and
completeness still require human judgment.

## Scaling is outside this demo

Before multi-user hosting, add authentication, authorization, secure document retention and deletion,
job claims, a database suited to concurrent writers, request/rate/resource limits, and an explicit
model-data agreement. Preserve idempotent publication and pending-approval semantics. Do not run
multiple API workers against the current single-process command lock.
