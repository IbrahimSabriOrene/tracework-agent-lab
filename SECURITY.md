# Security boundaries

Tracework is a single-user local educational application. Do not expose its unauthenticated API
to the internet or load real confidential documents into a publicly shared instance.

- Compose binds the published port to `127.0.0.1`.
- Review input is bounded plain text. Optional PDF upload uses an isolated, pinned local MinerU worker
  with fixed Basic/CPU configuration; there is no user-selected command or file-path execution.
- PDFs are limited to 5 MiB / 5 pages; encrypted/malformed files and oversized extraction are rejected.
  Uploaded bytes are temporary. Extracted text, provenance, and bounded failure logs stay in `.data/`.
- Worker model source is local after explicit setup; cloud OCR, global MinerU config, and LLM-assisted
  postprocessing are not used. Installing models requires network access; opening Pages does not.
- Exact source evidence and strict typed human decisions are checked outside the reviewer.
- Cross-origin browser mutations and untrusted Host headers are rejected. These are not authentication.
- Model endpoints are server configuration, not browser input. Optional Ollama receives source text.
- SQLite files, experiment artifacts, virtual environments, and environment files are Git-ignored.
- The hosted Pages site is static playback. It has no model secrets and makes no document-upload request.

Source quotes can still support an incorrect interpretation. These boundaries do not establish
general prompt-injection immunity, semantic correctness, or production security.
For imported PDFs, quote checks validate the extracted/corrected text, not the original PDF glyphs.
The subprocess is dependency isolation with a deadline, not an OS security sandbox for hostile PDFs.

Before multi-user deployment, add authentication, per-user authorization, retention/deletion rules,
secure transport, resource limits, and a concurrency-safe job/approval model.

If you find a vulnerability, avoid posting secrets or private documents in an issue. Use GitHub's
private vulnerability reporting if enabled, or contact the repository owner privately.
