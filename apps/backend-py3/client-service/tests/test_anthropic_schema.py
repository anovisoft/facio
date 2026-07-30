"""Anthropic JSON Schema normalization must keep fields named ``title``."""

from __future__ import annotations

import json
from typing import Any

from app.providers.anthropic_llm import _anthropic_json_schema
from app.schemas.create_response import CREATE_RESPONSE_SCHEMA
from app.schemas.path_state import PATH_RESPONSE_SCHEMA


def _defs(schema: dict) -> dict:
    return schema.get("$defs") or schema.get("definitions") or {}


def _walk(node: Any, visit) -> None:
    if isinstance(node, dict):
        visit(node)
        for value in node.values():
            _walk(value, visit)
    elif isinstance(node, list):
        for item in node:
            _walk(item, visit)


def _schema_metrics(schema: dict) -> dict[str, int]:
    any_of = 0
    any_of_null = 0
    descriptions = 0

    def visit(node: dict) -> None:
        nonlocal any_of, any_of_null, descriptions
        # Metadata descriptions are strings; PathGroup.properties.description is a schema.
        desc = node.get("description")
        if isinstance(desc, str):
            descriptions += 1
        branches = node.get("anyOf")
        if isinstance(branches, list):
            any_of += 1
            types = [
                b.get("type")
                for b in branches
                if isinstance(b, dict)
            ]
            if "null" in types:
                any_of_null += 1
        typ = node.get("type")
        if isinstance(typ, list) and "null" in typ:
            any_of_null += 1

    _walk(schema, visit)
    dumped = json.dumps(schema, ensure_ascii=False)
    return {
        "anyOf": any_of,
        "anyOf_null": any_of_null,
        "descriptions": descriptions,
        "chars": len(dumped),
    }


def test_create_schema_keeps_title_properties() -> None:
    out = _anthropic_json_schema(CREATE_RESPONSE_SCHEMA)
    defs = _defs(out)

    for name in ("PathGroup", "PathAction", "PathChecklistItem"):
        assert name in defs, f"missing $defs.{name}"
        props = defs[name].get("properties") or {}
        assert "title" in props, f"{name}.properties.title was stripped"
        assert "title" in (defs[name].get("required") or []), (
            f"{name}.required missing title"
        )


def test_path_schema_keeps_title_properties() -> None:
    out = _anthropic_json_schema(PATH_RESPONSE_SCHEMA)
    defs = _defs(out)

    for name in ("PathGroup", "PathAction", "PathChecklistItem"):
        props = defs[name].get("properties") or {}
        assert "title" in props
        assert "title" in (defs[name].get("required") or [])


def test_schema_metadata_title_still_stripped() -> None:
    raw = {
        "title": "Wrapper",
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "type": "string",
                "minLength": 1,
            },
            "sort": {"type": "integer", "default": 0},
        },
        "required": ["title"],
    }
    out = _anthropic_json_schema(raw)
    assert "title" not in out  # JSON Schema metadata key
    assert "title" in out["properties"]
    assert "title" not in out["properties"]["title"]  # field metadata
    assert "minLength" not in out["properties"]["title"]
    assert out["required"] == ["title", "sort"]


def test_wire_schema_collapses_nullable_anyof() -> None:
    out = _anthropic_json_schema(PATH_RESPONSE_SCHEMA)
    metrics = _schema_metrics(out)
    assert metrics["anyOf_null"] == 0
    assert metrics["anyOf"] == 0
    assert metrics["descriptions"] == 0

    defs = _defs(out)
    action = defs["PathAction"]["properties"]
    assert action["id"] == {"type": "string"}
    assert action["estimate_min"] == {"type": "integer"}
    assert action["group_id"] == {"type": "string"}
    day = defs["PathDay"]["properties"]
    assert day["title"] == {"type": "string"}
    assert day["summary"] == {"type": "string"}


def test_wire_schema_size_smoke() -> None:
    """Guard against grammar blow-ups (Slice 2 cycle/days + future plugins)."""
    path = _anthropic_json_schema(PATH_RESPONSE_SCHEMA)
    create = _anthropic_json_schema(CREATE_RESPONSE_SCHEMA)
    path_m = _schema_metrics(path)
    create_m = _schema_metrics(create)

    # Pre-fix Path wire was ~7.6k chars with 11 nullable anyOf + descriptions.
    assert path_m["chars"] < 4500, path_m
    assert create_m["chars"] < 5500, create_m
    assert path_m["anyOf_null"] == 0
    assert create_m["anyOf_null"] == 0
    assert create_m["descriptions"] == 0


def test_create_wire_requires_both_branches_as_objects() -> None:
    out = _anthropic_json_schema(CREATE_RESPONSE_SCHEMA)
    props = out["properties"]
    # Collapsed PathState | null → $ref / InstantAnswer | null → $ref
    assert props["path"] == {"$ref": "#/$defs/PathState"}
    assert props["instant_answer"] == {"$ref": "#/$defs/InstantAnswerPayload"}
    assert "path" in out["required"]
    assert "instant_answer" in out["required"]
