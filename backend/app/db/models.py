from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    github_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    github_login: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (Index("idx_users_github_login", "github_login"),)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    access_token_ct: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    access_token_nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("idx_sessions_user_id", "user_id"),
        Index("idx_sessions_expires_at", "expires_at"),
    )


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    target_login: Mapped[str] = mapped_column(Text, nullable=False)
    target_github_id: Mapped[int | None] = mapped_column(BigInteger)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    share_slug: Mapped[str | None] = mapped_column(Text, unique=True)
    latest_run_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "analysis_runs.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_analyses_latest_run_id",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="analyses")
    runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        foreign_keys="AnalysisRun.analysis_id",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "target_login", name="uq_analyses_user_target"),
        Index("idx_analyses_user_id", "user_id"),
        Index("idx_analyses_target_login", "target_login"),
    )


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    analysis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    total_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tier_name: Mapped[str] = mapped_column(Text, nullable=False)
    scores_hash: Mapped[str] = mapped_column(Text, nullable=False)
    ingestion_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingestion_completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    ingestion_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    analysis: Mapped[Analysis] = relationship(
        back_populates="runs", foreign_keys=[analysis_id]
    )
    narratives: Mapped[list["Narrative"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        Index("idx_runs_analysis_id", "analysis_id"),
        Index("idx_runs_analysis_completed", "analysis_id", "ingestion_completed_at"),
    )


class Narrative(Base):
    __tablename__ = "narratives"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    analysis_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False
    )
    mode: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    is_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped[AnalysisRun] = relationship(back_populates="narratives")

    __table_args__ = (
        CheckConstraint(
            "mode IN ('roast','mentor','recruiter','cto','career')",
            name="ck_narratives_mode",
        ),
        UniqueConstraint("analysis_run_id", "mode", name="uq_narratives_run_mode"),
        Index("idx_narratives_run_id", "analysis_run_id"),
    )
