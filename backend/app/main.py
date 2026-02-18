from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.schemas.error import ErrorDetail, ErrorDetails, ErrorResponse


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: ErrorDetails = None,
) -> JSONResponse:
    payload = ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump())


def _validation_error_details(exc: RequestValidationError) -> list[dict[str, str]]:
    details: list[dict[str, str]] = []
    for error in exc.errors():
        raw_location = error.get("loc", ())
        normalized_location = [
            str(item) for item in raw_location if item not in {"body", "query", "path"}
        ]
        field = (
            ".".join(normalized_location) if normalized_location else "non_field_error"
        )
        details.append(
            {
                "field": field,
                "message": str(error.get("msg", "Invalid value")),
            }
        )
    return details


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(
        _request: Request,
        exc: AppException,
    ) -> JSONResponse:
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return build_error_response(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=_validation_error_details(exc),
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exception_handler(
        _request: Request,
        _exc: RateLimitExceeded,
    ) -> JSONResponse:
        return build_error_response(
            status_code=429,
            code="RATE_LIMITED",
            message="Too many requests. Please try again later.",
            details=None,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger = structlog.get_logger(__name__)
        logger.exception("unhandled_exception", exception=str(exc))
        return build_error_response(
            status_code=500,
            code="INTERNAL_ERROR",
            message="Internal server error",
            details=None,
        )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="App", lifespan=lifespan)
    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
