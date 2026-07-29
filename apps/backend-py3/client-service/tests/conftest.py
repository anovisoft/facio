"""Shared fixtures: test Postgres, mocked LLM, HTTP client."""

from __future__ import annotations

import os
from collections import defaultdict, deque
from collections.abc import AsyncIterator, Callable
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Configure test env before app import (settings are lru_cached).
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://fasio:fasio@localhost:5435/fasio_test",
)
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["LOG_DIR"] = ""
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.config import get_settings
from app.database import Base, get_db
from app.deps import provide_llm
from app.main import app
from app.models import (  # noqa: F401 — register metadata
    Action,
    ActionGroup,
    ChecklistItem,
    ConversationTurn,
    Event,
    LlmCall,
    Project,
    StateVersion,
    User,
)
from app.providers.llm import (
    LLMProvider,
    LLMPurpose,
    LLMRawResult,
    set_llm_provider,
)
from tests.factories import refined_path_state, sample_create_path, sample_path_state

get_settings.cache_clear()

TEST_DATABASE_URL = os.environ["DATABASE_URL"]
DEVICE_HEADER = {"X-Device-Id": "test-device"}


class ScriptedLLMProvider(LLMProvider):
    """Queues raw JSON responses per purpose (create / refine / repair)."""

    def __init__(self) -> None:
        self._queues: dict[str, deque[Any]] = defaultdict(deque)
        self.calls: list[dict[str, Any]] = []

    def enqueue(self, purpose: LLMPurpose, raw_response: Any) -> None:
        self._queues[purpose].append(raw_response)

    def clear(self) -> None:
        self._queues.clear()
        self.calls.clear()

    async def generate(
        self,
        *,
        purpose: LLMPurpose,
        messages: list[dict[str, Any]],
        response_schema: dict[str, Any],
    ) -> LLMRawResult:
        self.calls.append(
            {
                "purpose": purpose,
                "messages": messages,
                "response_schema": response_schema,
            }
        )
        queue = self._queues[purpose]
        if not queue:
            raise RuntimeError(
                f"No scripted LLM response for purpose={purpose!r}. "
                f"Remaining queues: {{k: len(v) for k, v in self._queues.items()}}"
            )
        raw = queue.popleft()
        return LLMRawResult(
            model="test-model",
            raw_response=raw,
            tokens_in=10,
            tokens_out=20,
            latency_ms=1,
        )


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncIterator[AsyncSession]:
    session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        # Truncate between tests (CASCADE clears FKs).
        table_names = ", ".join(
            f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
        )
        if table_names:
            await session.execute(text(f"TRUNCATE {table_names} CASCADE"))
            await session.commit()
        yield session
        await session.rollback()


@pytest.fixture
def llm() -> ScriptedLLMProvider:
    provider = ScriptedLLMProvider()
    set_llm_provider(provider)
    return provider


@pytest.fixture
async def client(
    db_session: AsyncSession, llm: ScriptedLLMProvider
) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[provide_llm] = lambda: llm

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def device_id() -> str:
    return f"device-{uuid4().hex[:12]}"


@pytest.fixture
def auth_headers(device_id: str) -> dict[str, str]:
    return {"X-Device-Id": device_id}


@pytest.fixture
def enqueue_path(llm: ScriptedLLMProvider) -> Callable[..., None]:
    def _enqueue(**overrides: Any) -> None:
        llm.enqueue("create", sample_create_path(**overrides))

    return _enqueue


@pytest.fixture
def enqueue_refine(llm: ScriptedLLMProvider) -> Callable[..., None]:
    def _enqueue(state: dict[str, Any] | None = None) -> None:
        llm.enqueue("refine", state or refined_path_state())

    return _enqueue


@pytest.fixture
def enqueue_repair(llm: ScriptedLLMProvider) -> Callable[..., None]:
    def _enqueue(state: dict[str, Any] | None = None) -> None:
        llm.enqueue("repair", state or sample_path_state(questions=[]))

    return _enqueue
