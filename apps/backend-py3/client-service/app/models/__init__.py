from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    abandoned = "abandoned"
    completed = "completed"


class ActionStatus(str, enum.Enum):
    pending = "pending"
    done = "done"
    skipped = "skipped"


class ConversationRole(str, enum.Enum):
    user = "user"
    assistant = "assistant"
    system = "system"


class StateSource(str, enum.Enum):
    llm_create = "llm_create"
    llm_refine = "llm_refine"
    llm_repair = "llm_repair"
    llm_next_cycle = "llm_next_cycle"
    user_restore = "user_restore"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    projects: Mapped[list[Project]] = relationship(
        back_populates="user", lazy="selectin"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ProjectStatus.draft,
    )
    raw_intent: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    paraphrase: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    horizon: Mapped[str | None] = mapped_column(Text, nullable=True)
    domain: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    # Guide Cover (Facio 0.1 Slice B) — glance fields for Continue / drawer.
    cover_emoji: Mapped[str | None] = mapped_column(String(16), nullable=True)
    cover_difficulty: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    cover_duration_summary: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    cycle_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cycle_horizon_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cycle_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cycle_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedule_days: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    committed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cycle_anchor_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cycle_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    cycles_history: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="projects")
    groups: Mapped[list[ActionGroup]] = relationship(
        back_populates="project",
        lazy="selectin",
        order_by="ActionGroup.sort",
        cascade="all, delete-orphan",
    )
    actions: Mapped[list[Action]] = relationship(
        back_populates="project",
        lazy="selectin",
        order_by="Action.sort",
        cascade="all, delete-orphan",
    )


class ActionGroup(Base):
    """Path section (Покупки, Готовка, …). `key` is the LLM-facing id."""

    __tablename__ = "action_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    project: Mapped[Project] = relationship(back_populates="groups")
    actions: Mapped[list[Action]] = relationship(back_populates="group")


class Action(Base):
    __tablename__ = "actions"
    __table_args__ = (
        UniqueConstraint("project_id", "key", name="uq_actions_project_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("action_groups.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimate_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[ActionStatus] = mapped_column(
        Enum(
            ActionStatus,
            name="action_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ActionStatus.pending,
    )
    timers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    counter: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timeline: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    interval_plan: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    stepper: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="actions")
    group: Mapped[ActionGroup | None] = relationship(
        back_populates="actions", lazy="selectin"
    )
    checklist_items: Mapped[list[ChecklistItem]] = relationship(
        back_populates="action",
        lazy="selectin",
        order_by="ChecklistItem.sort",
        cascade="all, delete-orphan",
    )


class ChecklistItem(Base):
    __tablename__ = "checklist_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    action_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("actions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    action: Mapped[Action] = relationship(back_populates="checklist_items")


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    role: Mapped[ConversationRole] = mapped_column(
        Enum(
            ConversationRole,
            name="conversation_role",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_messages: Mapped[list | dict] = mapped_column(JSONB, nullable=False)
    raw_response: Mapped[dict | list | str | None] = mapped_column(
        JSONB, nullable=True
    )
    parsed_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StateVersion(Base):
    __tablename__ = "state_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    source: Mapped[StateSource] = mapped_column(
        Enum(
            StateSource,
            name="state_source",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
