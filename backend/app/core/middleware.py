"""Application HTTP middleware registration (CORS, request-ID correlation, security headers)."""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.logging import request_id_var
from app.core.settings import settings


def register_middleware(app: FastAPI) -> None:
    """Attach CORS, request-ID correlation, and security headers middleware."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    @app.middleware("http")
    async def add_security_and_request_id_headers(request: Request, call_next):
        """Attach a request ID for log correlation and add security headers to every response."""
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(req_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
