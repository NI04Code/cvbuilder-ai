"""Unit tests for app.core.middleware."""

import httpx
import pytest
from fastapi import FastAPI

from app.core.logging import request_id_var
from app.core.middleware import register_middleware


@pytest.mark.asyncio
async def test_register_middleware_sets_security_and_request_id_headers():
    test_app = FastAPI()
    register_middleware(test_app)

    @test_app.get("/ping")
    async def ping():
        return {"req_id": request_id_var.get()}

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.get("/ping", headers={"X-Request-ID": "trace-42"})
        r2 = await client.get("/ping")

    assert r1.headers["X-Request-ID"] == "trace-42"
    assert r1.json()["req_id"] == "trace-42"
    assert len(r2.headers["X-Request-ID"]) == 32
    assert r1.headers["X-Content-Type-Options"] == "nosniff"
    assert r1.headers["X-Frame-Options"] == "DENY"
    assert r1.headers["X-XSS-Protection"] == "1; mode=block"
    assert r1.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert r1.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert request_id_var.get() == "-"
