"""stdio adapter over DeskSession. Tool names are TOOL_NAMES; schemas from talk spec."""

from __future__ import annotations

import json
from datetime import datetime

from facio_domain.desk import founding_desk
from facio_domain.tools import TOOL_NAMES
from mcp.server import Server, ServerRequestContext
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
)

from facio_api.mcp.session import DeskSession
from facio_api.talk.spec import tool_schemas


def mcp_tools() -> list[Tool]:
    """OpenAI-shaped talk schemas, advertised in TOOL_NAMES order."""
    by_name = {row["function"]["name"]: row["function"] for row in tool_schemas()}
    return [
        Tool(
            name=name,
            description=by_name[name]["description"],
            input_schema=by_name[name]["parameters"],
        )
        for name in TOOL_NAMES
    ]


def make_server(session: DeskSession | None = None) -> Server:
    held = session if session is not None else DeskSession(founding_desk(), now=datetime.now())
    advertised = mcp_tools()

    async def list_tools(
        _ctx: ServerRequestContext,
        _params: PaginatedRequestParams | None,
    ) -> ListToolsResult:
        return ListToolsResult(tools=advertised)

    async def call_tool(
        _ctx: ServerRequestContext,
        params: CallToolRequestParams,
    ) -> CallToolResult:
        outcome = held.call(params.name, dict(params.arguments or {}))
        payload = {
            "ok": outcome.ok,
            "error": outcome.error,
            "data": outcome.data,
            "mutated": outcome.mutated,
        }
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=json.dumps(payload, ensure_ascii=False, default=str),
                )
            ],
            is_error=not outcome.ok,
        )

    return Server("facio", on_list_tools=list_tools, on_call_tool=call_tool)


async def run_stdio(session: DeskSession | None = None) -> None:
    server = make_server(session)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )
