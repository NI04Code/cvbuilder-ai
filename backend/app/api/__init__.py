"""API router aggregation."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.resume import router as resume_router
from app.api.profile import router as profile_router
from app.api.cv import router as cv_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(resume_router)
api_router.include_router(profile_router)
api_router.include_router(cv_router)
