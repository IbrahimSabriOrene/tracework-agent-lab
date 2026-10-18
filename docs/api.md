# Local API

Base URL: `http://127.0.0.1:8765`. Interactive OpenAPI documentation: `/docs`.
This unauthenticated API is for one local user. GitHub Pages does not host it.
FastAPI's standard Swagger page loads its vendor assets from jsDelivr; the main review UI is
self-contained. Use `/openapi.json` when working without access to the documentation CDN.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/api/health` | Actual engine and persistence mode |
| GET | `/api/documents` | Synthetic source documents; expected labels excluded |
| GET | `/api/profiles` | Allowlisted review profiles |
| GET | `/api/runs` | Most recent 30 local review IDs |
| POST | `/api/reviews` | Execute a real graph until human approval |
| POST | `/api/pdf/extract` | Multipart `file` PDF; local MinerU extraction only, no review or approval |
| GET | `/api/reviews/{id}` | Restore state, findings, withheld evidence, and trace |
| POST | `/api/reviews/{id}/decision` | Resume a pending graph with a strict boolean decision |
| GET | `/api/reviews/{id}/report` | Read the published local report; 404 before approval |
| GET | `/api/evaluation` | Deterministic fixture metrics for both profiles |
| POST | `/api/experiments` | Run one isolated Harness² experiment; POSIX only |

## Start a review

```bash
curl -X POST http://127.0.0.1:8765/api/reviews \
  -H 'Content-Type: application/json' \
  -d '{"title":"Example brief","document":"# Example\nDelivery owner: TBD.\nReview next Friday.","profile":"evidence"}'
```

The response includes `run_id`, `status: awaiting_review`, exact-quote `findings`, `rejected`
unsupported findings, `trace`, and `can_decide: true`. Keep the UUID returned by the API.

## Human decision

```bash
curl -X POST http://127.0.0.1:8765/api/reviews/REPLACE_WITH_RUN_UUID/decision \
  -H 'Content-Type: application/json' \
  -d '{"approved":true,"note":"Checked the evidence against the source."}'
```

`approved` must be a JSON boolean, not a string. `false` ends the workflow without publication.
A repeated decision returns 409. Unknown IDs return 404; malformed UUIDs or schema failures return
422. Unknown profiles and invalid workflow transitions return 409.

## PDF import

Prepare the [local MinerU worker](pdf.md), then upload a PDF:

```bash
curl -X POST http://127.0.0.1:8765/api/pdf/extract -F 'file=@web/samples/atlas-scan.pdf'
```

The 201 response contains `import_id`, `title`, `document`, and `source` provenance. Inspect the
text, then supply it to `POST /api/reviews` with `pdf_import_id` set to that returned UUID.
The API resolves provenance from its own local extraction record; it is not supplied by the browser.
Edited text is allowed and recorded as `source.text_edited`. The existing human decision step still
applies. Reports retain PDF provenance through checkpoint restart.

Missing worker/models return 503; excessive PDF bytes return 413; invalid/encrypted PDFs and page/text
limits return 422; a concurrent extraction returns 409; worker failure returns 502; timeout returns 504.
`/api/health` includes setup indicators under `pdf`. GitHub Pages has neither endpoint nor worker.

## Experiment

```bash
curl -X POST http://127.0.0.1:8765/api/experiments \
  -H 'Content-Type: application/json' -d '{"mode":"sequential"}'
```

Only `sequential` or `parallel` is accepted. The API fixes the recursion budget to 1. A concurrent
experiment receives 409. The response includes actual execution receipts and explicitly identifies
the editor as scripted. This endpoint never uses the interactive review's Ollama setting.

## Input boundaries

Titles are 1–150 characters; documents are 20–20,000 characters; notes are at most 1,000 characters.
Extra request fields are rejected. Browser mutations from another Origin are rejected. Trusted
hosts are localhost, 127.0.0.1, and the test client host. These checks are not authentication and
do not make public deployment safe. Only the dedicated PDF endpoint accepts binary input (5 MiB,
5 pages). No arbitrary file path, command, parser URL, or cloud OCR option is accepted.
