"""Add unique constraint on submissions(task_id, agent_id).

Revision ID: 002
Revises: 001
Create Date: 2026-03-13
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_submission_task_agent", "submissions", ["task_id", "agent_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_submission_task_agent", "submissions", type_="unique")
