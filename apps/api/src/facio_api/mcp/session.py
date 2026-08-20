"""In-process desk session: RFC tools via apply_tool. Desk is a snapshot here."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from facio_domain.models import CueOrigin, Desk
from facio_domain.tools import TOOL_NAMES, ToolOutcome, apply_tool

MCP_ORIGIN = CueOrigin(chat_id="mcp")


class DeskSession:
    """Hold one desk snapshot and apply the same 16 names as talk."""

    def __init__(self, desk: Desk, *, now: datetime, pain: bool = False) -> None:
        self.desk = desk
        self.now = now
        self.pain = pain

    def names(self) -> list[str]:
        return list(TOOL_NAMES)

    def call(self, name: str, arguments: dict[str, Any] | None) -> ToolOutcome:
        outcome = apply_tool(
            self.desk,
            name,
            arguments,
            origin=MCP_ORIGIN,
            pain=self.pain,
            now=self.now,
        )
        self.desk = outcome.desk
        return outcome
