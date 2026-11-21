"""Unit tests for app.core.exceptions."""

import httpx
import pytest
from fastapi import FastAPI

from app.core.exceptions import (
    BadRequestError,
    GenerationError,
    NotFoundError,
    UnauthorizedError,
    register_exception_handlers,
)


@pytest.mark.asyncio
async def test_register_exception_handlers_maps_all_errors():
    test_app = FastAPI()
    register_exception_handlers(test_app)

    @test_app.get("/bad")
    async def bad():
        raise BadRequestError("bad input")

    @test_app.get("/unauth")
    async def unauth():
        raise UnauthorizedError("denied")

    @test_app.get("/missing")
    async def missing():
        raise NotFoundError("not here")

    @test_app.get("/gen")
    async def gen():
        raise GenerationError("llm down")

    @test_app.get("/boom")
    async def boom():
        raise RuntimeError("sensitive internal trace")

    transport = httpx.ASGITransport(app=test_app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r_bad = await client.get("/bad")
        r_unauth = await client.get("/unauth")
        r_missing = await client.get("/missing")
        r_gen = await client.get("/gen")
        r_boom = await client.get("/boom")

    assert r_bad.status_code == 400 and r_bad.json()["detail"] == "bad input"
    assert r_unauth.status_code == 401 and r_unauth.headers["WWW-Authenticate"] == "Bearer"
    assert r_missing.status_code == 404 and r_missing.json()["detail"] == "not here"
    assert r_gen.status_code == 500 and r_gen.json()["detail"] == "llm down"
    assert r_boom.status_code == 500
    assert "sensitive internal trace" not in r_boom.text
