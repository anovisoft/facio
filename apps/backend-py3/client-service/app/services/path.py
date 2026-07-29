from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import (
    ConflictError,
    NotConfiguredError,
    NotFoundError,
    UpstreamError,
    ValidationAppError,
)
from app.models import (
    ConversationRole,
    ConversationTurn,
    Event,
    Project,
    ProjectStatus,
    StateSource,
    StateVersion,
    User,
)
from app.providers.llm import (
    LLMNotConfiguredError,
    LLMProvider,
    LLMPurpose,
    get_llm_provider,
)
from app.schemas.api import (
    ConversationTurnResponse,
    TimelineEntry,
    TimelineResponse,
)
from app.schemas.path_state import PathState
from app.services.audit import AuditService, EventType
from app.services.path_llm import (
    PATH_RESPONSE_SCHEMA,
    messages_for_create,
    messages_for_refine,
    messages_for_repair,
    parse_path_state,
)
from app.services.path_materialize import (
    apply_contract,
    ensure_action_keys,
    materialize_path,
)
from app.services.project import ProjectService


@dataclass
class ApplyResult:
    state: PathState
    version: int
    llm_call_id: UUID


class PathService:
    def __init__(
        self,
        db: AsyncSession,
        llm: LLMProvider | None = None,
    ) -> None:
        self.db = db
        self.llm = llm or get_llm_provider()
        self.audit = AuditService(db)
        self.projects = ProjectService(db)

    async def create_from_intent(self, user: User, intent: str) -> Project:
        await self.audit.add_event(
            event_type=EventType.intent_submitted,
            user_id=user.id,
            payload={"intent": intent},
        )

        project = Project(
            user_id=user.id,
            status=ProjectStatus.draft,
            raw_intent=intent,
        )
        self.db.add(project)
        await self.db.flush()

        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.user,
            content=intent,
            meta={"kind": "intent"},
        )

        result = await self._run_llm_mutation(
            user=user,
            project=project,
            purpose="create",
            messages=messages_for_create(intent),
            source=StateSource.llm_create,
            materialize="none",
        )
        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.assistant,
            content=result.state.paraphrase,
            meta={
                "kind": "soft_start",
                "outcome": result.state.outcome,
                "state_version": result.version,
                "llm_call_id": str(result.llm_call_id),
                "source": StateSource.llm_create.value,
            },
        )
        await self.audit.add_event(
            event_type=EventType.draft_shown,
            user_id=user.id,
            project_id=project.id,
            payload={"outcome": result.state.outcome, "version": result.version},
        )
        await self.db.commit()
        return await self.projects.get_project(user, project.id)

    async def refine(
        self,
        user: User,
        project_id: UUID,
        *,
        answer: str,
        question_id: str | None = None,
    ) -> Project:
        project = await self.projects.get_project(
            user, project_id, for_update=True
        )
        if project.status != ProjectStatus.draft:
            raise ConflictError("Only draft projects can be refined")

        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.user,
            content=answer,
            meta={"kind": "refine_answer", "question_id": question_id},
        )
        await self.audit.add_event(
            event_type=EventType.refine_answered,
            user_id=user.id,
            project_id=project.id,
            payload={"question_id": question_id},
        )

        _, current = await self.projects.get_latest_state(project.id)
        if current is None:
            raise ConflictError("Project has no Path state to refine")

        result = await self._run_llm_mutation(
            user=user,
            project=project,
            purpose="refine",
            messages=messages_for_refine(
                current_state=current.model_dump(mode="json"),
                answer=answer,
                question_id=question_id,
            ),
            source=StateSource.llm_refine,
            materialize="none",
        )
        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.assistant,
            content=result.state.paraphrase,
            meta={
                "kind": "refine_result",
                "state_version": result.version,
                "llm_call_id": str(result.llm_call_id),
                "source": StateSource.llm_refine.value,
                "question_id": question_id,
            },
        )
        await self.db.commit()
        return await self.projects.get_project(user, project.id)

    async def repair(
        self,
        user: User,
        project_id: UUID,
        *,
        reason: str,
    ) -> Project:
        project = await self.projects.get_project(
            user, project_id, for_update=True
        )
        if project.status not in {ProjectStatus.active, ProjectStatus.draft}:
            raise ConflictError("Project cannot be repaired in current status")

        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.user,
            content=reason,
            meta={"kind": "repair_reason"},
        )
        await self.audit.add_event(
            event_type=EventType.repair_requested,
            user_id=user.id,
            project_id=project.id,
            payload={"reason": reason},
        )

        _, current = await self.projects.get_latest_state(project.id)
        if current is None:
            raise ConflictError("Project has no Path state to repair")

        materialize = (
            "merge" if project.status == ProjectStatus.active else "none"
        )
        result = await self._run_llm_mutation(
            user=user,
            project=project,
            purpose="repair",
            messages=messages_for_repair(
                current_state=current.model_dump(mode="json"),
                reason=reason,
                project_status=project.status.value,
            ),
            source=StateSource.llm_repair,
            materialize=materialize,
        )
        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.assistant,
            content=result.state.paraphrase,
            meta={
                "kind": "repair_result",
                "state_version": result.version,
                "llm_call_id": str(result.llm_call_id),
                "source": StateSource.llm_repair.value,
            },
        )
        await self.audit.add_event(
            event_type=EventType.repair_applied,
            user_id=user.id,
            project_id=project.id,
            payload={"version": result.version},
        )
        await self.db.commit()
        return await self.projects.get_project(user, project.id)

    async def get_transcript(
        self, user: User, project_id: UUID
    ) -> list[ConversationTurnResponse]:
        await self.projects.get_project(user, project_id)
        turns = await self._load_turns(project_id)
        versions = await self._load_versions_by_number(project_id)
        return [self._turn_response(t, versions) for t in turns]

    async def get_timeline(
        self, user: User, project_id: UUID
    ) -> TimelineResponse:
        await self.projects.get_project(user, project_id)
        turns = await self._load_turns(project_id)
        versions = await self._load_versions_by_number(project_id)
        events = await self._load_events(project_id)

        entries: list[TimelineEntry] = []
        for turn in turns:
            meta = turn.meta or {}
            version_no = meta.get("state_version")
            state = None
            if isinstance(version_no, int) and version_no in versions:
                state = PathState.model_validate(versions[version_no].state_json)
            llm_call_id = None
            raw_id = meta.get("llm_call_id")
            if raw_id:
                try:
                    llm_call_id = UUID(str(raw_id))
                except ValueError:
                    llm_call_id = None
            entries.append(
                TimelineEntry(
                    at=turn.created_at,
                    kind=str(meta.get("kind") or turn.role.value),
                    turn=self._turn_response(turn, versions),
                    state_version=version_no if isinstance(version_no, int) else None,
                    state=state,
                    llm_call_id=llm_call_id,
                )
            )
        for event in events:
            entries.append(
                TimelineEntry(
                    at=event.created_at,
                    kind=f"event:{event.type}",
                    event_type=event.type,
                    event_payload=event.payload,
                    state_version=(
                        event.payload.get("version")
                        or event.payload.get("new_version")
                        if isinstance(event.payload, dict)
                        else None
                    ),
                )
            )
        entries.sort(key=lambda e: e.at)
        return TimelineResponse(project_id=project_id, entries=entries)

    async def restore_state(
        self,
        user: User,
        project_id: UUID,
        *,
        version: int,
    ) -> Project:
        """Append a restored PathState snapshot (draft JSON SoT only)."""
        project = await self.projects.get_project(
            user, project_id, for_update=True
        )
        if project.status != ProjectStatus.draft:
            raise ConflictError("Only draft projects can restore a prior state")

        result = await self.db.execute(
            select(StateVersion).where(
                StateVersion.project_id == project.id,
                StateVersion.version == version,
            )
        )
        snapshot = result.scalar_one_or_none()
        if snapshot is None:
            raise NotFoundError(f"State version {version} not found")

        try:
            state = ensure_action_keys(
                PathState.model_validate(snapshot.state_json)
            )
        except ValidationError as exc:
            raise ValidationAppError(
                f"Stored state version {version} is invalid: {exc}"
            ) from exc

        apply_contract(project, state)
        new_version = await self._next_version(project.id)
        await self.audit.add_state_version(
            project_id=project.id,
            version=new_version,
            state_json=state.model_dump(mode="json"),
            source=StateSource.user_restore,
        )
        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.system,
            content=f"Restored Path to version {version}",
            meta={
                "kind": "state_restored",
                "restored_from_version": version,
                "state_version": new_version,
                "source": StateSource.user_restore.value,
            },
        )
        await self.audit.add_event(
            event_type=EventType.back_navigated,
            user_id=user.id,
            project_id=project.id,
            payload={
                "restored_from_version": version,
                "new_version": new_version,
            },
        )
        await self.db.commit()
        return await self.projects.get_project(user, project.id)

    async def _run_llm_mutation(
        self,
        *,
        user: User,
        project: Project,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        source: StateSource,
        materialize: str,
    ) -> ApplyResult:
        """Shared create/refine/repair LLM pipeline. Does not commit."""
        try:
            raw = await self.llm.generate(
                purpose=purpose,
                messages=messages,
                response_schema=PATH_RESPONSE_SCHEMA,
            )
        except LLMNotConfiguredError as exc:
            await self.audit.add_llm_call(
                project_id=project.id,
                purpose=purpose,
                prompt_messages=messages,
                parsed_ok=False,
                error=str(exc),
            )
            await self.audit.add_event(
                event_type=EventType.plan_failed,
                user_id=user.id,
                project_id=project.id,
                payload={"purpose": purpose, "error": str(exc)},
            )
            raise NotConfiguredError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            await self.audit.add_llm_call(
                project_id=project.id,
                purpose=purpose,
                prompt_messages=messages,
                parsed_ok=False,
                error=str(exc),
            )
            await self.audit.add_event(
                event_type=EventType.plan_failed,
                user_id=user.id,
                project_id=project.id,
                payload={"purpose": purpose, "error": str(exc)},
            )
            raise UpstreamError(f"LLM call failed: {exc}") from exc

        try:
            state = ensure_action_keys(parse_path_state(raw.raw_response))
        except (ValidationError, ValueError, TypeError, json.JSONDecodeError) as exc:
            await self.audit.add_llm_call(
                project_id=project.id,
                purpose=purpose,
                prompt_messages=messages,
                model=raw.model,
                raw_response=raw.raw_response,
                parsed_ok=False,
                tokens_in=raw.tokens_in,
                tokens_out=raw.tokens_out,
                latency_ms=raw.latency_ms,
                error=str(exc),
            )
            await self.audit.add_event(
                event_type=EventType.plan_failed,
                user_id=user.id,
                project_id=project.id,
                payload={"purpose": purpose, "error": str(exc)},
            )
            raise ValidationAppError(f"Invalid Path from LLM: {exc}") from exc

        llm_call = await self.audit.add_llm_call(
            project_id=project.id,
            purpose=purpose,
            prompt_messages=messages,
            model=raw.model,
            raw_response=raw.raw_response,
            parsed_ok=True,
            tokens_in=raw.tokens_in,
            tokens_out=raw.tokens_out,
            latency_ms=raw.latency_ms,
        )

        version = await self._next_version(project.id)
        await self.audit.add_state_version(
            project_id=project.id,
            version=version,
            state_json=state.model_dump(mode="json"),
            source=source,
        )
        apply_contract(project, state)

        if materialize == "full":
            await materialize_path(self.db, project, state, merge_progress=False)
        elif materialize == "merge":
            await materialize_path(self.db, project, state, merge_progress=True)
        elif materialize != "none":
            raise ValueError(f"Unknown materialize mode: {materialize}")

        return ApplyResult(
            state=state, version=version, llm_call_id=llm_call.id
        )

    async def _next_version(self, project_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(StateVersion.version), 0)).where(
                StateVersion.project_id == project_id
            )
        )
        return int(result.scalar_one()) + 1

    async def _load_turns(self, project_id: UUID) -> list[ConversationTurn]:
        result = await self.db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.project_id == project_id)
            .order_by(ConversationTurn.created_at.asc())
        )
        return list(result.scalars().all())

    async def _load_versions_by_number(
        self, project_id: UUID
    ) -> dict[int, StateVersion]:
        result = await self.db.execute(
            select(StateVersion)
            .where(StateVersion.project_id == project_id)
            .order_by(StateVersion.version.asc())
        )
        return {row.version: row for row in result.scalars().all()}

    async def _load_events(self, project_id: UUID) -> list[Event]:
        result = await self.db.execute(
            select(Event)
            .where(Event.project_id == project_id)
            .order_by(Event.created_at.asc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _turn_response(
        turn: ConversationTurn,
        versions: dict[int, StateVersion],
    ) -> ConversationTurnResponse:
        meta = turn.meta or {}
        state = None
        version_no = meta.get("state_version")
        if isinstance(version_no, int) and version_no in versions:
            try:
                state = PathState.model_validate(
                    versions[version_no].state_json
                )
            except ValidationError:
                state = None
        return ConversationTurnResponse(
            id=turn.id,
            project_id=turn.project_id,
            role=turn.role.value,
            content=turn.content,
            meta=turn.meta,
            created_at=turn.created_at,
            state=state,
        )
