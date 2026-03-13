"""Add claimed_at and submitted_at columns to tasks table.

Revision ID: 004
Revises: 003
Create Date: 2026-03-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tasks", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tasks", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tasks", "submitted_at")
    op.drop_column("tasks", "claimed_at")
