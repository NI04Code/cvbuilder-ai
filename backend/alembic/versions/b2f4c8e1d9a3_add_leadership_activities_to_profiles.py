"""add_leadership_activities_to_profiles

Revision ID: b2f4c8e1d9a3
Revises: 6c138618cdd2
Create Date: 2026-11-13 22:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2f4c8e1d9a3'
down_revision: Union[str, None] = '6c138618cdd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add leadership_activities JSONB column to profiles."""
    op.add_column(
        'profiles',
        sa.Column('leadership_activities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Remove leadership_activities column from profiles."""
    op.drop_column('profiles', 'leadership_activities')

