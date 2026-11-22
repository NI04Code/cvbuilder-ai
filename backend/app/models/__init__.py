"""ORM model exports — import all models here so Alembic can discover them."""

from app.models.cold_email import GeneratedColdEmail
from app.models.cover_letter import GeneratedCoverLetter
from app.models.generated_cv import GeneratedCV
from app.models.job_application import JobApplication
from app.models.profile import Profile
from app.models.user import OAuthAccount, User

__all__ = [
    "User",
    "OAuthAccount",
    "Profile",
    "GeneratedCV",
    "GeneratedCoverLetter",
    "GeneratedColdEmail",
    "JobApplication",
]
