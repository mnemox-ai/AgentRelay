"""Add api_key column to agents table.

Revision ID: 003
Revises: 002
Create Date: 2026-03-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("api_key", sa.String(64), nullable=False))
    op.create_unique_constraint("uq_agents_api_key", "agents", ["api_key"])
    op.create_index("ix_agents_api_key", "agents", ["api_key"])


def downgrade() -> None:
    op.drop_index("ix_agents_api_key", table_name="agents")
    op.drop_constraint("uq_agents_api_key", "agents", type_="unique")
    op.drop_column("agents", "api_key")
