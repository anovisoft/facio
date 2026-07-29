from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import (
    Action,
    ActionGroup,
    ActionStatus,
    ChecklistItem,
    ConversationRole,
    ConversationTurn,
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
from app.schemas.path import PATH_RESPONSE_SCHEMA, PathState
from app.services.audit import AuditService
from app.services.project import ProjectService


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
    ) -> Project:
        await self.audit.add_event(
            event_type="intent_submitted",
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

        messages = [
            {
                "role": "system",
                "content": (
                    "Create a structured Path for the user's intent. "
                    "Every action must include a non-empty why. "
                    "Respond with JSON matching the provided schema."
                ),
            },
            {"role": "user", "content": intent},
        ]
        state = await self._call_and_apply(
            user=user,
            project=project,
            purpose="create",
            messages=messages,
            source=StateSource.llm_create,
        )

        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.assistant,
            content=state.paraphrase,
            meta={"kind": "soft_start", "outcome": state.outcome},
        )
        await self.audit.add_event(
            event_type="draft_created",
            user_id=user.id,
            project_id=project.id,
            payload={"outcome": state.outcome},
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
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only draft projects can be refined",
            )

        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.user,
            content=answer,
            meta={"kind": "refine_answer", "question_id": question_id},
        )
        await self.audit.add_event(
            event_type="refine_submitted",
            user_id=user.id,
            project_id=project.id,
            payload={"question_id": question_id},
        )

        _, current_state = await self.projects.get_latest_state(project.id)
        messages = [
            {
                "role": "system",
                "content": (
                    "Refine the Path using the user's clarification. "
                    "Keep why non-empty on every action. "
                    "Respond with JSON matching the provided schema."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "current_state": current_state,
                        "question_id": question_id,
                        "answer": answer,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        state = await self._call_and_apply(
            user=user,
            project=project,
            purpose="refine",
            messages=messages,
            source=StateSource.llm_refine,
        )
        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.assistant,
            content=state.paraphrase,
            meta={"kind": "refine_result"},
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
        if project.status not in {
            ProjectStatus.active,
            ProjectStatus.draft,
        }:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project cannot be repaired in current status",
            )

        await self.audit.add_turn(
            project_id=project.id,
            role=ConversationRole.user,
            content=reason,
            meta={"kind": "repair_reason"},
        )
        await self.audit.add_event(
            event_type="repair_requested",
            user_id=user.id,
            project_id=project.id,
            payload={"reason": reason},
        )

        _, current_state = await self.projects.get_latest_state(project.id)
        messages = [
            {
                "role": "system",
                "content": (
                    "Repair / recompute the Path for the given reason. "
                    "Preserve completed progress where possible. "
                    "Every action must include a non-empty why."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "current_state": current_state,
                        "reason": reason,
                        "project_status": project.status.value,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        await self._call_and_apply(
            user=user,
            project=project,
            purpose="repair",
            messages=messages,
            source=StateSource.llm_repair,
            preserve_done=True,
        )
        await self.db.commit()
        return await self.projects.get_project(user, project.id)

    async def get_transcript(
        self, user: User, project_id: UUID
    ) -> list[ConversationTurn]:
        await self.projects.get_project(user, project_id)
        result = await self.db.execute(
            select(ConversationTurn)
            .where(ConversationTurn.project_id == project_id)
            .order_by(ConversationTurn.created_at.asc())
        )
        return list(result.scalars().all())

    async def _call_and_apply(
        self,
        *,
        user: User,
        project: Project,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        source: StateSource,
        preserve_done: bool = False,
    ) -> PathState:
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
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=str(exc),
            ) from exc
        except Exception as exc:  # noqa: BLE001
            await self.audit.add_llm_call(
                project_id=project.id,
                purpose=purpose,
                prompt_messages=messages,
                parsed_ok=False,
                error=str(exc),
            )
            await self.audit.add_event(
                event_type="plan_failed",
                user_id=user.id,
                project_id=project.id,
                payload={"purpose": purpose, "error": str(exc)},
            )
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"LLM call failed: {exc}",
            ) from exc

        try:
            state = self._parse_state(raw.raw_response)
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
                event_type="plan_failed",
                user_id=user.id,
                project_id=project.id,
                payload={"purpose": purpose, "error": str(exc)},
            )
            await self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid Path from LLM: {exc}",
            ) from exc

        await self.audit.add_llm_call(
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
        await self._materialize_actions(project, state, preserve_done=preserve_done)
        return state

    def _parse_state(self, raw_response: Any) -> PathState:
        if isinstance(raw_response, PathState):
            return raw_response
        if isinstance(raw_response, str):
            data = json.loads(raw_response)
        elif isinstance(raw_response, dict):
            data = raw_response
        else:
            raise TypeError(
                f"Unexpected raw_response type: {type(raw_response)!r}"
            )
        return PathState.model_validate(data)

    async def _next_version(self, project_id: UUID) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(StateVersion.version), 0)).where(
                StateVersion.project_id == project_id
            )
        )
        current = result.scalar_one()
        return int(current) + 1

    async def _materialize_actions(
        self,
        project: Project,
        state: PathState,
        *,
        preserve_done: bool,
    ) -> None:
        done_titles: set[str] = set()
        if preserve_done:
            for action in project.actions:
                if action.status == ActionStatus.done:
                    done_titles.add(action.title)

            for action in list(project.actions):
                if action.status != ActionStatus.done:
                    await self.db.delete(action)
            await self.db.flush()
        else:
            for action in list(project.actions):
                await self.db.delete(action)
            await self.db.flush()

        for group in list(project.groups):
            # Keep groups still referenced by preserved done actions
            if preserve_done and any(
                a.group_id == group.id and a.status == ActionStatus.done
                for a in project.actions
            ):
                continue
            await self.db.delete(group)
        await self.db.flush()

        project.outcome = state.outcome
        project.paraphrase = state.paraphrase
        project.success_criteria = state.success_criteria
        project.horizon = state.horizon

        key_to_group: dict[str, ActionGroup] = {
            g.key: g for g in project.groups
        }
        for group_spec in sorted(state.groups, key=lambda g: g.sort):
            existing = key_to_group.get(group_spec.id)
            if existing is not None:
                existing.title = group_spec.title
                existing.sort = group_spec.sort
                key_to_group[group_spec.id] = existing
                continue
            group = ActionGroup(
                project_id=project.id,
                key=group_spec.id,
                title=group_spec.title,
                sort=group_spec.sort,
            )
            self.db.add(group)
            await self.db.flush()
            key_to_group[group_spec.id] = group

        for index, item in enumerate(state.actions):
            if preserve_done and item.title in done_titles:
                continue
            sort = item.sort if item.sort is not None else index
            group_uuid = None
            if item.group_id is not None:
                group_uuid = key_to_group[item.group_id].id
            action = Action(
                project_id=project.id,
                group_id=group_uuid,
                title=item.title,
                why=item.why,
                detail=item.detail,
                estimate_min=item.estimate_min,
                sort=sort,
                status=ActionStatus.pending,
            )
            self.db.add(action)
            await self.db.flush()
            for c_index, checklist in enumerate(item.checklist_items):
                self.db.add(
                    ChecklistItem(
                        action_id=action.id,
                        key=checklist.id,
                        title=checklist.title,
                        done=checklist.done,
                        sort=checklist.sort
                        if checklist.sort is not None
                        else c_index,
                    )
                )

        await self.db.flush()
        await self.db.refresh(
            project, attribute_names=["actions", "groups"]
        )
