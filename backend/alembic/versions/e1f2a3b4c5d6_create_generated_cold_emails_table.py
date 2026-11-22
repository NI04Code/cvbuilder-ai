"""create_generated_cold_emails_table

Revision ID: e1f2a3b4c5d6
Revises: c4d9e2f1a8b7
Create Date: 2026-11-21 22:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'c4d9e2f1a8b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create generated_cold_emails table."""
    op.create_table(
        'generated_cold_emails',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('recruiter_name', sa.String(length=255), nullable=True),
        sa.Column('job_description', sa.Text(), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('email_body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_generated_cold_emails_user_id'),
        'generated_cold_emails',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    """Drop generated_cold_emails table."""
    op.drop_index(
        op.f('ix_generated_cold_emails_user_id'),
        table_name='generated_cold_emails',
    )
    op.drop_table('generated_cold_emails')
