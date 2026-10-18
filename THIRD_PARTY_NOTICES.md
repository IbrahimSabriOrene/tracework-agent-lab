# Third-party notices

Original Tracework application code is provided under the MIT license.

## Harness²

- Source: https://github.com/google-research/harness2
- Pinned commit: `1cfe254e8d25b15f37048c3730134686abe60335`
- Package version at that commit: `0.1.0`
- License: Apache License 2.0; see the dependency's LICENSE file.
- Copyright: Google LLC, as specified in upstream source files.

Tracework imports the upstream core and text-tree schema as a separate dependency. It does not
vendor upstream source or replace its license. Our document adapter, reviewer, application,
teaching fixtures, and UI are original code. Upstream benchmark datasets are not distributed here.

Harness² is a research project and is not an officially supported Google product.
No Google endorsement or ready-made upstream LangGraph integration is claimed.

## Optional MinerU worker

- Source: https://github.com/opendatalab/MinerU
- Pinned package: `mineru==4.0.12`, installed into a separate optional environment.
- License: [MinerU Open Source License](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md),
  Apache License 2.0 with additional terms, including online-service attribution and commercial thresholds.
- Model weights have their own terms. The Basic ONNX files are downloaded from the upstream model
  repositories during setup and are not redistributed in this Git repository or static site.
- Tracework identifies MinerU in the PDF interface, extraction metadata, reports, and documentation.

The worker calls the local Python SDK. Neither MinerU source nor weights are relicensed as MIT by
this application. Review upstream and individual model terms before redistribution or other use.

## Other dependencies

LangGraph, FastAPI, Uvicorn, Pydantic, and their transitive dependencies retain their respective
licenses. The complete resolved dependency set is recorded in `uv.lock`. Do not treat this notice
as a relicensing of any dependency.
