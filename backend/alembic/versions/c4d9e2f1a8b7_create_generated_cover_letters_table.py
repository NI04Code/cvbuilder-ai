"""create_generated_cover_letters_table

Revision ID: c4d9e2f1a8b7
Revises: b2f4c8e1d9a3
Create Date: 2026-11-15 18:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c4d9e2f1a8b7'
down_revision: Union[str, None] = 'b2f4c8e1d9a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create generated_cover_letters table."""
    op.create_table(
        'generated_cover_letters',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('job_title', sa.String(length=255), nullable=True),
        sa.Column('company_name', sa.String(length=255), nullable=True),
        sa.Column('job_description', sa.Text(), nullable=False),
        sa.Column('cover_letter_text', sa.Text(), nullable=False),
        sa.Column('pdf_file_path', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_generated_cover_letters_user_id'),
        'generated_cover_letters',
        ['user_id'],
        unique=False,
    )


def downgrade() -> None:
    """Drop generated_cover_letters table."""
    op.drop_index(op.f('ix_generated_cover_letters_user_id'), table_name='generated_cover_letters')
    op.drop_table('generated_cover_letters')

