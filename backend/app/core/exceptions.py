"""Domain exceptions and FastAPI exception handler registration."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """Base exception for application service-layer failures."""

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class BadRequestError(ServiceError):
    """Raised when a business precondition or input constraint fails."""


class UnauthorizedError(ServiceError):
    """Raised when authentication or token verification fails."""


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist or is not owned by the caller."""


class GenerationError(ServiceError):
    """Raised when AI workflow execution or PDF rendering fails."""


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain and fallback exception handlers on the FastAPI application."""

    @app.exception_handler(BadRequestError)
    async def bad_request_error_handler(request: Request, exc: BadRequestError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": exc.detail},
        )

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_error_handler(request: Request, exc: UnauthorizedError):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.detail},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(NotFoundError)
    async def not_found_error_handler(request: Request, exc: NotFoundError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.detail},
        )

    @app.exception_handler(GenerationError)
    async def generation_error_handler(request: Request, exc: GenerationError):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch-all handler to log unexpected errors and prevent stack traces from leaking."""
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )
