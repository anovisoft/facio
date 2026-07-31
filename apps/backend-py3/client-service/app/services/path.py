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
from app.database import async_session_maker
from app.schemas.api import (
    ConversationTurnResponse,
    CreateIntentResponse,
    InstantAnswerResponse,
    PathCreatedResponse,
    TimelineEntry,
    TimelineResponse,
)
from app.schemas.create_response import (
    CreateGateResponse,
    InstantAnswerPayload,
    PathStartSurface,
)
from app.schemas.path_state import PathState
from app.services.audit import AuditService, EventType
from app.services.path_llm import (
    CREATE_GATE_SCHEMA,
    PATH_RESPONSE_SCHEMA,
    messages_for_create_gate,
    messages_for_create_path,
    messages_for_refine,
    messages_for_repair,
    parse_create_gate,
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


@dataclass(frozen=True)
class PendingPathJob:
    """Returned to the API layer so BackgroundTasks can finish phase-2."""

    project_id: UUID
    user_id: UUID
    intent: str
    path_start: PathStartSurface
    gate_llm_call_id: UUID


def _assistant_content(raw_response: Any) -> str:
    if isinstance(raw_response, str):
        return raw_response
    return json.dumps(raw_response, ensure_ascii=False)


def _parse_create_gate_payload(raw_response: Any) -> CreateGateResponse:
    return parse_create_gate(raw_response)


def _parse_path_payload(raw_response: Any) -> PathState:
    state = ensure_action_keys(parse_path_state(raw_response))
    if not state.actions:
        raise ValueError("Path must include at least one action")
    return state


def path_state_from_start(start: PathStartSurface) -> PathState:
    """Minimal PathState for progressive create phase-1 (no actions/plugins)."""
    titles = [t.strip() for t in start.outline_days if t.strip()]
    if not titles:
        titles = [start.title.strip()[:120] or "Plan"]
    horizon = max(1, len(titles))
    days = [
        {
            "day_index": i,
            "kind": "other",
            "title": title[:120],
            "summary": "",
        }
        for i, title in enumerate(titles)
    ]
    questions = [
        {
            "id": q.id.strip(),
            "prompt": q.prompt.strip(),
            "options": [o for o in q.options if o.strip()],
        }
        for q in start.questions
    ]
    # Build via dict so PathState before-validators see cycle as a mapping
    # (PathCycle instances get wiped to {} by backfill_missing_fields).
    return PathState.model_validate(
        {
            "title": start.title.strip()[:120],
            "summary": start.summary.strip()[:600],
            "outcome": start.title.strip()[:120],
            "paraphrase": start.paraphrase.strip(),
            "success_criteria": start.summary.strip()[:600],
            "horizon": "…",
            "domain": "other",
            "tags": [],
            "cycle": {
                "index": 1,
                "horizon_days": horizon,
                "status": "draft",
                "goal_for_cycle": "",
            },
            "days": days,
            "groups": [],
            "actions": [],
            "questions": questions,
            "resources": [],
            "milestones": [],
        }
    )


async def complete_create_path_job(
    *,
    project_id: UUID,
    user_id: UUID,
    intent: str,
    path_start: dict[str, Any],
    gate_llm_call_id: UUID,
) -> None:
    """Background phase-2: full Path + plugins after slim start returned."""
    start = PathStartSurface.model_validate(path_start)
    async with async_session_maker() as db:
        try:
            service = PathService(db, llm=get_llm_provider())
            user = await db.get(User, user_id)
            if user is None:
                logger.error(
                    "complete_create_path_job: user missing user=%s project=%s",
                    user_id,
                    project_id,
                )
                return
            await service.complete_create_path(
                user=user,
                project_id=project_id,
                intent=intent,
                path_start=start,
                gate_llm_call_id=gate_llm_call_id,
            )
        except Exception:
            logger.exception(
                "complete_create_path_job failed project=%s user=%s",
                project_id,
                user_id,
            )
            await db.rollback()


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
    ) -> tuple[CreateIntentResponse, PendingPathJob | None]:
        """Phase-1 create: gate (+ start surface). Path body runs in background.

        Returns ``(response, pending_job)``. Caller schedules ``pending_job``
        via BackgroundTasks when not None.
        """
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

        messages = messages_for_create_gate(intent)
        gate, _gate_raw, gate_llm_call_id = await self._generate_create_gate(
            user=user,
            messages=messages,
        )

        if gate.kind == "instant_answer":
            assert gate.instant_answer is not None
            response = await self._finish_instant_answer(
                user=user,
                intent=intent,
                user_turn_id=user_turn.id,
                payload=gate.instant_answer,
                llm_call_id=gate_llm_call_id,
            )
            return response, None

        assert gate.path_start is not None
        start = gate.path_start
        state = path_state_from_start(start)

        project = Project(
            user_id=user.id,
            status=ProjectStatus.draft,
            raw_intent=intent,
        )
        self.db.add(project)
        await self.db.flush()

        intent_event.project_id = project.id
        user_turn.project_id = project.id
        llm_row = await self.db.get(LlmCall, gate_llm_call_id)
        if llm_row is not None:
            llm_row.project_id = project.id

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
                "gate_llm_call_id": str(gate_llm_call_id),
                "path_ready": False,
                "source": StateSource.llm_create.value,
            },
        )
        await self.audit.add_event(
            event_type=EventType.soft_start_shown,
            user_id=user.id,
            project_id=project.id,
            payload={
                "paraphrase": state.paraphrase,
                "outcome": state.outcome,
                "version": version,
                "path_ready": False,
            },
        )
        await self.db.commit()
        project = await self.projects.get_project(user, project.id)
        detail = await self.projects.to_detail(project)
        logger.info(
            "create path start user=%s project=%s version=%s outcome=%r "
            "gate_llm=%s path_ready=false",
            user.id,
            project.id,
            version,
            state.outcome,
            gate_llm_call_id,
        )
        job = PendingPathJob(
            project_id=project.id,
            user_id=user.id,
            intent=intent,
            path_start=start,
            gate_llm_call_id=gate_llm_call_id,
        )
        return PathCreatedResponse(kind="path", project=detail), job

    async def complete_create_path(
        self,
        *,
        user: User,
        project_id: UUID,
        intent: str,
        path_start: PathStartSurface,
        gate_llm_call_id: UUID,
    ) -> Project:
        """Phase-2: generate full Path+plugins and append state version."""
        project = await self.projects.get_project(
            user, project_id, for_update=True
        )
        if project.status != ProjectStatus.draft:
            logger.info(
                "complete_create_path skip non-draft project=%s status=%s",
                project_id,
                project.status,
            )
            return project

        _, current = await self.projects.get_latest_state(project.id)
        if current is not None and current.actions:
            logger.info(
                "complete_create_path skip already ready project=%s",
                project_id,
            )
            return project

        state, _path_raw, path_llm_call_id = await self._generate_create_path(
            user=user,
            project_id=project.id,
            messages=messages_for_create_path(intent, path_start=path_start),
        )

        llm_row = await self.db.get(LlmCall, path_llm_call_id)
        if llm_row is not None:
            llm_row.project_id = project.id

        state = ensure_action_keys(state)
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
                "kind": "path_ready",
                "outcome": state.outcome,
                "state_version": version,
                "llm_call_id": str(path_llm_call_id),
                "gate_llm_call_id": str(gate_llm_call_id),
                "path_ready": True,
                "source": StateSource.llm_create.value,
            },
        )
        await self.audit.add_event(
            event_type=EventType.draft_shown,
            user_id=user.id,
            project_id=project.id,
            payload={
                "outcome": state.outcome,
                "version": version,
                "path_ready": True,
            },
        )
        await self.db.commit()
        logger.info(
            "create path ready user=%s project=%s version=%s outcome=%r "
            "gate_llm=%s path_llm=%s",
            user.id,
            project.id,
            version,
            state.outcome,
            gate_llm_call_id,
            path_llm_call_id,
        )
        return await self.projects.get_project(user, project.id)

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

    async def _generate_create_gate(
        self,
        *,
        user: User,
        messages: list[dict[str, Any]],
    ) -> tuple[CreateGateResponse, LLMRawResult, UUID]:
        # Tiny schema: {kind, instant_answer} — no PathState (grammar budget).
        return await self._llm_generate_validated(
            user=user,
            project_id=None,
            purpose="create",
            messages=messages,
            response_schema=CREATE_GATE_SCHEMA,
            parse=_parse_create_gate_payload,
            invalid_message="Invalid create gate from LLM",
        )

    async def _generate_create_path(
        self,
        *,
        user: User,
        messages: list[dict[str, Any]],
        project_id: UUID | None = None,
    ) -> tuple[PathState, LLMRawResult, UUID]:
        # PathState-only structured output (plugins included; no IA branch).
        return await self._llm_generate_validated(
            user=user,
            project_id=project_id,
            purpose="create",
            messages=messages,
            response_schema=PATH_RESPONSE_SCHEMA,
            parse=_parse_path_payload,
            invalid_message="Invalid Path from LLM",
        )

    async def refine(
        self,
        user: User,
        project_id: UUID,
        *,
        answers: list[dict[str, str]],
        comment: str | None = None,
    ) -> Project:
        project = await self.projects.get_project(
            user, project_id, for_update=True
        )
        if project.status != ProjectStatus.draft:
            raise ConflictError("Only draft projects can be refined")

        answer_lines = [
            f"{item['question_id']}: {item['value']}" for item in answers
        ]
        if comment:
            answer_lines.append(f"comment: {comment}")
        turn_content = "\n".join(answer_lines) if answer_lines else (comment or "")

        await self.audit.add_turn(
            user_id=user.id,
            project_id=project.id,
            role=ConversationRole.user,
            content=turn_content,
            meta={
                "kind": "refine_answer",
                "answers": answers,
                "comment": comment,
            },
        )
        await self.audit.add_event(
            event_type=EventType.refine_answered,
            user_id=user.id,
            project_id=project.id,
            payload={"answers": answers, "comment": comment},
        )

        _, current = await self.projects.get_latest_state(project.id)
        if current is None:
            raise ConflictError("Project has no Path state to refine")
        if not current.actions:
            raise ConflictError(
                "Path is still generating — wait until the plan is ready"
            )

        result = await self._run_llm_mutation(
            user=user,
            project=project,
            purpose="refine",
            messages=messages_for_refine(
                current_state=current.model_dump(mode="json"),
                answers=answers,
                comment=comment,
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
                "answers": answers,
                "comment": comment,
            },
        )
        await self.db.commit()
        logger.info(
            "refine project=%s version=%s answers=%s has_comment=%s",
            project.id,
            result.version,
            [a["question_id"] for a in answers],
            bool(comment),
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
