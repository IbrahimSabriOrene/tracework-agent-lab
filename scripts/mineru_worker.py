"""Executed by the isolated MinerU Python, never by the review engine."""

import importlib.metadata
import json
import sys
from pathlib import Path


def main():
    version = importlib.metadata.version("mineru")
    if version != "4.0.12":
        raise RuntimeError("Tracework requires MinerU 4.0.12; run scripts/setup_pdf.py.")
    from mineru.parser import parse

    # Explicit local SDK, CPU small models, no remote API or LLM-assisted postprocessing.
    result = parse(Path(sys.argv[1]), tier="basic", ocr_mode="auto", image_analysis=False)
    output = {"version": version, "document": result.markdown(), "pages": len(result.pages)}
    Path(sys.argv[2]).write_text(json.dumps(output, ensure_ascii=False), "utf-8")


if __name__ == "__main__":
    main()
