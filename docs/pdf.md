# Local PDF import with MinerU

[Türkçe rehber](pdf.tr.md) · [Testing](testing.md) · [API](api.md)

Tracework can import a PDF with **MinerU 4.0.12 Basic / ONNX on CPU**, then pass the extracted
text into the same LangGraph review, evidence verification, and human approval workflow.
There is no API key or paid OCR service. The optional worker is installed separately from the
lightweight review application. Model files are downloaded during setup; inference uses local
model files and the local Python SDK, with no cloud fallback.

![Actual local scanned-PDF review](images/pdf-import.png)

## Native setup: Windows, Linux, or macOS

From the repository root, install the base application and prepare the optional worker:

```bash
uv sync --locked
uv run python scripts/setup_pdf.py
uv run tracework serve
```

The setup script needs [uv](https://docs.astral.sh/uv/). It creates `.mineru/` using Python 3.12,
installs the pinned MinerU release, downloads the Basic/ONNX models, and verifies that the
required model files exist. Expect a substantial first download: the tested model set was
approximately 850 MB, in addition to the worker's Python packages. The worker uses CPU inference;
it does not require a GPU. Runtime and quality depend on the document and machine.

Open **http://127.0.0.1:8765**. If the application was already open during setup, reload the page.
`/api/health` exposes `pdf.installed`, `pdf.models_prepared`, and `pdf.available`. These are setup
indicators, not a claim that every PDF will parse successfully.

`TRACEWORK_DATA_DIR` selects the application's data directory, including the model cache. Use
the same value for setup and serving. `TRACEWORK_MINERU_PYTHON` can point to another isolated
Python interpreter containing exactly MinerU 4.0.12. The default is `.mineru/Scripts/python.exe`
on Windows and `.mineru/bin/python` elsewhere.

## Docker setup

The base image keeps OCR optional. Use the PDF override to install its separate environment:

```bash
docker compose -f compose.yaml -f compose.pdf.yaml up --build -d
docker compose -f compose.yaml -f compose.pdf.yaml exec lab /app/.venv/bin/python scripts/setup_pdf.py
```

After model preparation, reload **http://127.0.0.1:8765**. The existing named data volume retains
models, extracted text, review checkpoints, and reports. Model weights are not embedded in the
published repository or downloaded by opening GitHub Pages.

## Upload → inspect → review

1. Download the [synthetic scanned Atlas PDF](../web/samples/atlas-scan.pdf). It contains a page
   image and **no embedded text layer**, so the example requires actual OCR.
2. In the local application's **Import PDF · local MinerU** panel, choose the PDF and press
   **Extract text locally**. Wait for completion; CPU parsing can take minutes.
3. Check the displayed text against your PDF. Use **Edit document** if extraction needs correction.
   The original PDF remains on your computer; the server's upload copy is temporary.
4. Select **Evidence-aware** and press **Run review**. The included sample should produce three
   offline findings: unassigned owner, relative date, and pending dependency. Baseline finds one.
5. Inspect the exact quoted lines, then approve or reject publication. Only approval writes a
   local report. Download its JSON and inspect `source`.
6. Leave another review pending, restart the application with the same data, and restore it from
   **Recent local reviews**. The extracted text and PDF provenance remain in graph state.

PDF import does not make the deterministic reviewer a general document-understanding model.
The bundled rules inspect explicit English fixture patterns. Optional Ollama review is configured
separately; it may produce different findings and still needs human assessment.

## What the report preserves

| Field | Meaning |
| --- | --- |
| `source.filename` | Display filename, without an uploaded directory path |
| `source.pdf_sha256` | Hash of the original uploaded PDF bytes |
| `source.pages` | Original page count; partial extraction is rejected |
| `source.parser` / `parser_version` / `tier` | MinerU, 4.0.12, Basic |
| `source.extracted_text_sha256` | Hash of the initial extracted text |
| `source.text_edited` | Whether the reviewed text differs from that initial extraction |
| `source.import_id` | Persistent local extraction artifact identifier |
| `document_sha256` | Hash of the actual text that was reviewed |

**Evidence verification checks the extracted or corrected text.** It does not independently
verify PDF glyphs or OCR accuracy. Source line numbers refer to the text shown in the workbench,
not PDF coordinates or printed page-line numbers. The workflow does not render OCR HTML.

## Limits and data handling

- One PDF at a time; at most **5 MiB**, **5 pages**, and **20,000 extracted characters**.
- Large page dimensions, encrypted PDFs, malformed files, and empty/oversized extraction are rejected.
- There is no silent page skipping, text truncation, alternate OCR engine, or cloud fallback.
- The local worker has a 10-minute deadline. Upload copies and per-job temporary files are removed
  after processing. A bounded `.data/pdf-worker.log` is retained on worker failure.
- Extracted text and provenance remain under `.data/pdf-imports/`; review state and reports use
  the existing SQLite files. All of these are Git-ignored local data. Deleting a review does not
  have a UI in this demo; retain only synthetic material when demonstrating it.
- Setup writes an application-specific MinerU configuration. The worker selects local model source,
  CPU ONNX, and disables LLM-assisted postprocessing. It does not use the user's global MinerU config
  or a configured remote MinerU API. Basic parsing uses no document-library server.
- The hosted Pages site disables PDF upload/extraction and explains how to run it locally.

## Verify the integration

Behavioral API tests use a controlled worker response so that CI needs no model download:

```bash
uv run pytest tests/test_pdf.py -q
```

With the local server and models prepared, exercise **real OCR through the browser**:

```bash
uv run --with playwright playwright install chromium
uv run --with playwright python scripts/check_browser.py --pdf
```

This uploads the raster-only sample, checks the three expected findings, inspects a source line,
approves the report, verifies its downloaded provenance, and saves `docs/images/pdf-import.png`.
The ordinary CI browser run checks the app without requiring the optional OCR environment.

To regenerate the synthetic sample, run `.mineru/Scripts/python.exe scripts/create_pdf_sample.py`
on Windows, or `.mineru/bin/python scripts/create_pdf_sample.py` elsewhere. That authoring script
uses Pillow and ReportLab from the optional worker environment.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Import button disabled | Use the local app, run setup against the same data directory, then reload |
| Model download fails | Check network access to Hugging Face/ModelScope; rerun setup to reuse completed files |
| Worker returns 502 | Inspect `.data/pdf-worker.log`; rerun setup for the pinned package/model files |
| Worker times out | Try a smaller PDF; no partial review is created |
| Too much extracted text | Split the PDF before import; the application does not truncate it |
| Accurate OCR but no useful findings | The offline rules are narrow; configure the optional local reviewer or inspect manually |

## Upstream and license

MinerU is a separate dependency, not original Tracework code. Version 4.0.12 uses the
[MinerU Open Source License](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md),
which includes additional terms alongside Apache 2.0. Model files retain their own licenses.
See [third-party notices](../THIRD_PARTY_NOTICES.md), the
[local SDK](https://opendatalab.github.io/MinerU/usage/sdk_api/), and
[runtime tiers](https://opendatalab.github.io/MinerU/usage/tiers/).
