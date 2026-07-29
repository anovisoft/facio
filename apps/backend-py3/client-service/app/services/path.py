from __future__ import annotations

import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar
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
    LlmCall,
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
    LLMRawResult,
    get_llm_provider,
)
from app.schemas.api import (
    ConversationTurnResponse,
    CreateIntentResponse,
    InstantAnswerResponse,
    PathCreatedResponse,
    TimelineEntry,
    TimelineResponse,
)
from app.schemas.create_response import CreateLlmResponse, InstantAnswerPayload
from app.schemas.path_state import PathState
from app.services.audit import AuditService, EventType
from app.services.path_llm import (
    CREATE_RESPONSE_SCHEMA,
    PATH_RESPONSE_SCHEMA,
    messages_for_create,
    messages_for_refine,
    messages_for_repair,
    parse_create_response,
    parse_path_state,
)
from app.services.path_materialize import (
    apply_contract,
    ensure_action_keys,
    materialize_path,
)
from app.services.project import ProjectService

logger = logging.getLogger("app.path")

_LLM_MAX_ATTEMPTS = 2
_T = TypeVar("_T")
MaterializeMode = Literal["none", "merge"]


@dataclass
class ApplyResult:
    state: PathState
    version: int
    llm_call_id: UUID


def _assistant_content(raw_response: Any) -> str:
    if isinstance(raw_response, str):
        return raw_response
    return json.dumps(raw_response, ensure_ascii=False)


def _parse_create_payload(raw_response: Any) -> CreateLlmResponse:
    parsed = parse_create_response(raw_response)
    if parsed.kind == "path" and parsed.path is not None:
        PathState.model_validate(parsed.path.model_dump(mode="json"))
    return parsed


def _parse_path_payload(raw_response: Any) -> PathState:
    return ensure_action_keys(parse_path_state(raw_response))


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

    async def create_from_intent(
        self, user: User, intent: str
    ) -> CreateIntentResponse:
        intent_event = await self.audit.add_event(
            event_type=EventType.intent_submitted,
            user_id=user.id,
            payload={"intent": intent},
        )

        user_turn = await self.audit.add_turn(
            user_id=user.id,
            project_id=None,
            role=ConversationRole.user,
            content=intent,
            meta={"kind": "intent"},
        )

        messages = messages_for_create(intent)
        parsed, raw, llm_call_id = await self._generate_create_response(
            user=user,
            messages=messages,
        )

        if parsed.kind == "instant_answer":
            assert parsed.instant_answer is not None
            return await self._finish_instant_answer(
                user=user,
                intent=intent,
                user_turn_id=user_turn.id,
                payload=parsed.instant_answer,
                llm_call_id=llm_call_id,
            )

        assert parsed.path is not None
        project = Project(
            user_id=user.id,
            status=ProjectStatus.draft,
            raw_intent=intent,
        )
        self.db.add(project)
        await self.db.flush()

        intent_event.project_id = project.id
        user_turn.project_id = project.id
        llm_row = await self.db.get(LlmCall, llm_call_id)
        if llm_row is not None:
            llm_row.project_id = project.id

        state = ensure_action_keys(parsed.path)
        version = await self._next_version(project.id)
        await self.audit.add_state_version(
            project_id=project.id,
            version=version,
            state_json=state.model_dump(mode="json"),
            source=StateSource.llm_create,
        )
        apply_contract(project, state)

        await self.audit.add_turn(
            user_id=user.id,
            project_id=project.id,
            role=ConversationRole.assistant,
            content=state.paraphrase,
            meta={
                "kind": "soft_start",
                "outcome": state.outcome,
                "state_version": version,
                "llm_call_id": str(llm_call_id),
                "source": StateSource.llm_create.value,
            },
        )
        # Soft-start and draft share one create composition in MVP UI; both
        # funnel events are written here so KPIs do not depend on client beacons.
        await self.audit.add_event(
            event_type=EventType.soft_start_shown,
            user_id=user.id,
            project_id=project.id,
            payload={
                "paraphrase": state.paraphrase,
                "outcome": state.outcome,
                "version": version,
            },
        )
        await self.audit.add_event(
            event_type=EventType.draft_shown,
            user_id=user.id,
            project_id=project.id,
            payload={"outcome": state.outcome, "version": version},
        )
        await self.db.commit()
        project = await self.projects.get_project(user, project.id)
        detail = await self.projects.to_detail(project)
        logger.info(
            "create path user=%s project=%s version=%s outcome=%r",
            user.id,
            project.id,
            version,
            state.outcome,
        )
        return PathCreatedResponse(kind="path", project=detail)

    async def _finish_instant_answer(
        self,
        *,
        user: User,
        intent: str,
        user_turn_id: UUID,
        payload: InstantAnswerPayload,
        llm_call_id: UUID,
    ) -> InstantAnswerResponse:
        assistant_turn = await self.audit.add_turn(
            user_id=user.id,
            project_id=None,
            role=ConversationRole.assistant,
            content=payload.answer,
            meta={
                "kind": "instant_answer",
                "label": payload.label,
                "goal_suggestions": payload.goal_suggestions,
                "llm_call_id": str(llm_call_id),
            },
        )
        event = await self.audit.add_event(
            event_type=EventType.instant_answer_shown,
            user_id=user.id,
            project_id=None,
            payload={
                "intent": intent,
                "label": payload.label,
                "answer": payload.answer,
                "goal_suggestions": payload.goal_suggestions,
                "domain": payload.domain,
                "llm_call_id": str(llm_call_id),
                "user_turn_id": str(user_turn_id),
                "assistant_turn_id": str(assistant_turn.id),
            },
        )
        await self.db.commit()
        logger.info(
            "create instant_answer user=%s llm_call=%s label=%r domain=%s",
            user.id,
            llm_call_id,
            payload.label,
            payload.domain,
        )
        return InstantAnswerResponse(
            kind="instant_answer",
            label=payload.label,
            answer=payload.answer,
            goal_suggestions=payload.goal_suggestions,
            raw_intent=intent,
            llm_call_id=llm_call_id,
            event_id=event.id,
            domain=payload.domain,
        )

    async def _generate_create_response(
        self,
        *,
        user: User,
        messages: list[dict[str, Any]],
    ) -> tuple[CreateLlmResponse, LLMRawResult, UUID]:
        return await self._llm_generate_validated(
            user=user,
            project_id=None,
            purpose="create",
            messages=messages,
            response_schema=CREATE_RESPONSE_SCHEMA,
            parse=_parse_create_payload,
            invalid_message="Invalid create response from LLM",
        )

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
            user_id=user.id,
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
            user_id=user.id,
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
        logger.info(
            "refine project=%s version=%s question_id=%s",
            project.id,
            result.version,
            question_id,
        )
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
            user_id=user.id,
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

        materialize: MaterializeMode = (
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
            user_id=user.id,
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
        logger.info(
            "repair project=%s version=%s status=%s",
            project.id,
            result.version,
            project.status.value,
        )
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
            user_id=user.id,
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

    async def _llm_generate_validated(
        self,
        *,
        user: User,
        project_id: UUID | None,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
        parse: Callable[[Any], _T],
        invalid_message: str,
    ) -> tuple[_T, LLMRawResult, UUID]:
        """Generate structured LLM output with validate + retry (×2)."""
        working_messages = list(messages)
        last_error: Exception | None = None

        for attempt in range(_LLM_MAX_ATTEMPTS):
            try:
                raw = await self.llm.generate(
                    purpose=purpose,
                    messages=working_messages,
                    response_schema=response_schema,
                )
            except LLMNotConfiguredError as exc:
                await self.audit.add_llm_call(
                    user_id=user.id,
                    project_id=project_id,
                    purpose=purpose,
                    prompt_messages=working_messages,
                    parsed_ok=False,
                    error=str(exc),
                )
                await self.audit.add_event(
                    event_type=EventType.plan_failed,
                    user_id=user.id,
                    project_id=project_id,
                    payload={"purpose": purpose, "error": str(exc)},
                )
                raise NotConfiguredError(str(exc)) from exc
            except Exception as exc:  # noqa: BLE001
                await self.audit.add_llm_call(
                    user_id=user.id,
                    project_id=project_id,
                    purpose=purpose,
                    prompt_messages=working_messages,
                    parsed_ok=False,
                    error=str(exc),
                )
                await self.audit.add_event(
                    event_type=EventType.plan_failed,
                    user_id=user.id,
                    project_id=project_id,
                    payload={"purpose": purpose, "error": str(exc)},
                )
                raise UpstreamError(f"LLM call failed: {exc}") from exc

            try:
                parsed = parse(raw.raw_response)
            except (
                ValidationError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
                await self.audit.add_llm_call(
                    user_id=user.id,
                    project_id=project_id,
                    purpose=purpose,
                    prompt_messages=working_messages,
                    model=raw.model,
                    raw_response=raw.raw_response,
                    parsed_ok=False,
                    tokens_in=raw.tokens_in,
                    tokens_out=raw.tokens_out,
                    latency_ms=raw.latency_ms,
                    error=str(exc),
                )
                if attempt + 1 < _LLM_MAX_ATTEMPTS:
                    working_messages = [
                        *working_messages,
                        {
                            "role": "assistant",
                            "content": _assistant_content(raw.raw_response),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Previous response failed validation: "
                                f"{exc}. Return corrected JSON matching "
                                "the schema."
                            ),
                        },
                    ]
                    continue
                await self.audit.add_event(
                    event_type=EventType.plan_failed,
                    user_id=user.id,
                    project_id=project_id,
                    payload={"purpose": purpose, "error": str(exc)},
                )
                raise ValidationAppError(
                    f"{invalid_message}: {exc}"
                ) from exc

            llm_call = await self.audit.add_llm_call(
                user_id=user.id,
                project_id=project_id,
                purpose=purpose,
                prompt_messages=working_messages,
                model=raw.model,
                raw_response=raw.raw_response,
                parsed_ok=True,
                tokens_in=raw.tokens_in,
                tokens_out=raw.tokens_out,
                latency_ms=raw.latency_ms,
            )
            return parsed, raw, llm_call.id

        assert last_error is not None
        raise ValidationAppError(
            f"{invalid_message}: {last_error}"
        ) from last_error

    async def _run_llm_mutation(
        self,
        *,
        user: User,
        project: Project,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        source: StateSource,
        materialize: MaterializeMode,
    ) -> ApplyResult:
        """Refine/repair: validated Path → state version (+ optional merge)."""
        state, _raw, llm_call_id = await self._llm_generate_validated(
            user=user,
            project_id=project.id,
            purpose=purpose,
            messages=messages,
            response_schema=PATH_RESPONSE_SCHEMA,
            parse=_parse_path_payload,
            invalid_message="Invalid Path from LLM",
        )

        version = await self._next_version(project.id)
        await self.audit.add_state_version(
            project_id=project.id,
            version=version,
            state_json=state.model_dump(mode="json"),
            source=source,
        )
        apply_contract(project, state)

        if materialize == "merge":
            await materialize_path(
                self.db, project, state, merge_progress=True
            )

        return ApplyResult(
            state=state, version=version, llm_call_id=llm_call_id
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
