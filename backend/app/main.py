"""Part 1: health, configuration, request tracing and consistent errors."""
import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException

from .config import Settings

logger = logging.getLogger(__name__)


class LiveResponse(BaseModel):
    status: str
    project_id: str
    phase: int


class ReadyResponse(LiveResponse):
    required_dependencies: dict[str, str]
    optional_services: dict[str, str]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    app.state.settings = settings

    def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
        request_id = request.state.request_id
        return JSONResponse(
            status_code=status,
            content={"error": {"code": code, "message": message, "request_id": request_id}},
            headers={"X-Request-ID": request_id},
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        # Generate our own ID: arbitrary client headers are untrusted.
        request.state.request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("Unhandled request error id=%s", request.state.request_id)
            response = error_response(request, 500, "internal_error", "An unexpected error occurred")
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        response = error_response(request, exc.status_code, "http_error", str(exc.detail))
        if exc.headers:
            response.headers.update(exc.headers)
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Do not reflect submitted values or potentially sensitive validation input.
        return error_response(request, 422, "validation_error", "Request validation failed")

    @app.get("/health/live", response_model=LiveResponse)
    async def live():
        return LiveResponse(status="alive", project_id="GOV-CS-028", phase=1)

    @app.get("/health/ready", response_model=ReadyResponse)
    async def ready():
        # Successful app construction validates the only current prerequisite.
        # These future services are not probed and do not gate Part 1 readiness.
        return ReadyResponse(
            status="ready", project_id="GOV-CS-028", phase=1,
            required_dependencies={"configuration": "validated"},
            optional_services={"postgresql": "not_required_in_part_1",
                               "chroma": "not_required_in_part_1",
                               "ollama": "not_required_in_part_1"},
        )

    # Keep CORS outermost so even error responses have the allowed CORS headers.
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
        allow_methods=["GET"], allow_headers=["Accept", "Content-Type"],
        expose_headers=["X-Request-ID"],
    )
    return app


app = create_app()
