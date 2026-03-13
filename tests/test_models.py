"""Smoke tests — models import and table metadata is correct."""

from agentrelay.models import (
    Agent,
    Base,
    LedgerEntry,
    ReputationSnapshot,
    Submission,
    Task,
    ValidationRun,
)


class TestModelsMetadata:
    def test_all_tables_registered(self):
        table_names = set(Base.metadata.tables.keys())
        expected = {
            "agents",
            "tasks",
            "submissions",
            "validation_runs",
            "reputation_snapshots",
            "ledger_entries",
        }
        assert expected == table_names

    def test_agent_tablename(self):
        assert Agent.__tablename__ == "agents"

    def test_task_tablename(self):
        assert Task.__tablename__ == "tasks"

    def test_submission_tablename(self):
        assert Submission.__tablename__ == "submissions"

    def test_validation_run_tablename(self):
        assert ValidationRun.__tablename__ == "validation_runs"

    def test_reputation_snapshot_tablename(self):
        assert ReputationSnapshot.__tablename__ == "reputation_snapshots"

    def test_ledger_entry_tablename(self):
        assert LedgerEntry.__tablename__ == "ledger_entries"

    def test_agent_columns(self):
        cols = {c.name for c in Agent.__table__.columns}
        assert cols >= {"id", "name", "quota_profile", "capabilities", "status", "created_at", "updated_at"}

    def test_task_columns(self):
        cols = {c.name for c in Task.__table__.columns}
        assert cols >= {"id", "task_spec", "status", "publisher_id", "claimed_by", "reward", "deadline_at"}

    def test_task_foreign_keys(self):
        fk_targets = {str(fk.target_fullname) for fk in Task.__table__.foreign_keys}
        assert fk_targets == {"agents.id"}  # publisher_id + claimed_by both -> agents.id

    def test_submission_foreign_keys(self):
        fk_targets = {str(fk.target_fullname) for fk in Submission.__table__.foreign_keys}
        assert fk_targets == {"tasks.id", "agents.id"}

    def test_validation_run_foreign_keys(self):
        fk_targets = {str(fk.target_fullname) for fk in ValidationRun.__table__.foreign_keys}
        assert fk_targets == {"submissions.id"}

    def test_reputation_snapshot_foreign_keys(self):
        fk_targets = {str(fk.target_fullname) for fk in ReputationSnapshot.__table__.foreign_keys}
        assert fk_targets == {"agents.id"}

    def test_ledger_entry_foreign_keys(self):
        fk_targets = {str(fk.target_fullname) for fk in LedgerEntry.__table__.foreign_keys}
        assert fk_targets == {"agents.id", "tasks.id"}
