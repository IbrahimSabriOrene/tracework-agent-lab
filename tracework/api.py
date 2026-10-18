"""Local-only demo API. Hosted GitHub Pages uses generated replay fixtures instead."""

import os
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .documents import public_documents
from .evaluation import evaluate
from .reviewer import PROFILES
from .workflow import Lab

ROOT = Path(__file__).resolve().parent.parent


class NewReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=150)
    document: str = Field(min_length=20, max_length=20000)
    profile: str = "evidence"


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approved: bool = Field(strict=True)
    note: str = Field(default="", max_length=1000)


class ExperimentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str = Field(default="sequential", pattern="^(sequential|parallel)$")


def create_app(data_dir: Path | None = None, engine: str | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.lab = Lab(
            data_dir or Path(os.getenv("TRACEWORK_DATA_DIR", ".data")),
            engine or os.getenv("TRACEWORK_ENGINE", "offline"),
        )
        app.state.experiment_lock = threading.Lock()
        yield
        app.state.lab.close()

    app = FastAPI(title="Tracework Document Review Lab", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )

    @app.middleware("http")
    async def same_origin(request: Request, call_next):
        origin = request.headers.get("origin")
        expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
        if request.method not in {"GET", "HEAD", "OPTIONS"} and origin and origin != expected:
            return JSONResponse({"detail": "Cross-origin mutations are disabled."}, status_code=403)
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid content length."}, status_code=400)
        if content_length > 100000:
            return JSONResponse({"detail": "Request body is too large."}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
        )
        return response

    @app.exception_handler(ValueError)
    async def invalid_request(request, exc):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "Review or report not found."}, status_code=404)

    @app.get("/api/health")
    def health():
        return {
            "name": "Tracework",
            "mode": "local",
            "engine": app.state.lab.engine,
            "persistence": "SQLite",
            "framework": "LangGraph",
        }

    @app.get("/api/documents")
    def documents():
        return public_documents()

    @app.get("/api/profiles")
    def profiles():
        return PROFILES

    @app.get("/api/runs")
    def runs():
        return app.state.lab.list_runs()

    @app.post("/api/reviews", status_code=201)
    def start(review: NewReview):
        return app.state.lab.start(review.title, review.document, review.profile)

    def check_id(run_id):
        try:
            uuid.UUID(run_id)
        except ValueError as exc:
            raise HTTPException(422, "Invalid review identifier.") from exc

    @app.get("/api/reviews/{run_id}")
    def get_review(run_id: str):
        check_id(run_id)
        return app.state.lab.get(run_id)

    @app.post("/api/reviews/{run_id}/decision")
    def decision(run_id: str, choice: Decision):
        check_id(run_id)
        return app.state.lab.decide(run_id, choice.approved, choice.note)

    @app.get("/api/reviews/{run_id}/report")
    def report(run_id: str):
        check_id(run_id)
        return app.state.lab.report(run_id)

    @app.get("/api/evaluation")
    def evaluation():
        return {name: evaluate(name) for name in PROFILES}

    @app.post("/api/experiments")
    def experiment(settings: ExperimentRequest):
        from .harness_adapter import run_experiment

        if not app.state.experiment_lock.acquire(blocking=False):
            raise HTTPException(
                409, "An experiment is already running. Try again when it finishes."
            )
        try:
            root = data_dir or Path(os.getenv("TRACEWORK_DATA_DIR", ".data"))
            return run_experiment(root / "experiments" / str(uuid.uuid4()), settings.mode)
        finally:
            app.state.experiment_lock.release()

    app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
    return app
