"""One entry point for the local lab, reproducible evaluation and Harness² experiment."""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="tracework")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Open the local, persistent review lab")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    commands.add_parser("evaluate", help="Evaluate both profiles on held-out synthetic documents")
    experiment = commands.add_parser("experiment", help="Run the real Harness² core offline")
    experiment.add_argument("--mode", choices=["sequential", "parallel"], default="sequential")
    experiment.add_argument("--budget", type=int, choices=[1, 2], default=1)
    experiment.add_argument("--output", type=Path, default=Path(".data/experiment"))
    commands.add_parser(
        "export-replay", help="Generate the static walkthrough from actual graph runs"
    )
    args = parser.parse_args()
    if args.command == "serve":
        import uvicorn

        from .api import create_app

        uvicorn.run(create_app(), host=args.host, port=args.port)
    elif args.command == "evaluate":
        from .evaluation import evaluate

        print(json.dumps({key: evaluate(key) for key in ["baseline", "evidence"]}, indent=2))
    elif args.command == "experiment":
        from .harness_adapter import run_experiment

        result = run_experiment(args.output, args.mode, args.budget)
        print(json.dumps(result, indent=2))
    else:
        from .replay import export_replay

        export_replay()
