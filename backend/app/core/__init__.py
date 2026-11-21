"""Core application primitives: settings, logging, exceptions, and middleware."""

from app.core.exceptions import (
    BadRequestError,
    GenerationError,
    NotFoundError,
    ServiceError,
    UnauthorizedError,
    register_exception_handlers,
)
from app.core.logging import configure_logging, request_id_var
from app.core.middleware import register_middleware
from app.core.settings import Settings, settings

__all__ = [
    "BadRequestError",
    "GenerationError",
    "NotFoundError",
    "ServiceError",
    "Settings",
    "UnauthorizedError",
    "configure_logging",
    "register_exception_handlers",
    "register_middleware",
    "request_id_var",
    "settings",
]
