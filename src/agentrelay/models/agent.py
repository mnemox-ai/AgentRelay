"""Agent model."""

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Agent(TimestampMixin, Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    api_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    quota_profile: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    capabilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
