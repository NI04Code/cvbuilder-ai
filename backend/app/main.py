"""
CVBuilder AI — FastAPI Application Entry Point.

Wires middleware, exception handlers, rate limiting, API routes, and system probes.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.core import (
    configure_logging,
    register_exception_handlers,
    register_middleware,
    settings,
)
from app.database import check_db_connection, get_db
from app.security.rate_limiter import limiter

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    settings.validate_production_secrets()
    settings.upload_path
    settings.generated_path
    yield


app = FastAPI(
    title="CVBuilder AI API",
    description="AI-powered ATS CV generation from your resume and job descriptions.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate Limiting, Middleware & Exception Handlers ────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
register_middleware(app)
register_exception_handlers(app)

# ── Mount API Routes ──────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api")


# ── Health & Readiness Checks ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """Lightweight liveness check endpoint."""
    return {"status": "healthy", "service": "cvbuilder-ai-api"}


@app.get("/health/ready", tags=["System"])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check verifying database connectivity without disclosing internal details."""
    try:
        await check_db_connection(db)
    except Exception as exc:
        logger.error("Readiness check failed: database unreachable (%s)", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unavailable"},
        )
    return {"status": "ready", "service": "cvbuilder-ai-api"}
