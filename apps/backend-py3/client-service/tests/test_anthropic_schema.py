"""Anthropic JSON Schema normalization must keep fields named ``title``."""

from __future__ import annotations

import json
from typing import Any

from app.providers.anthropic_llm import _anthropic_json_schema
from app.schemas.create_response import CREATE_GATE_SCHEMA, CREATE_RESPONSE_SCHEMA
from app.schemas.path_state import PATH_RESPONSE_SCHEMA, PLUGINS_MATERIALIZE_SCHEMA


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


def test_gate_schema_keeps_instant_answer_fields() -> None:
    out = _anthropic_json_schema(CREATE_GATE_SCHEMA)
    props = out["properties"]
    assert set(props) == {"kind", "instant_answer", "path_start"}
    assert "path" not in props
    assert "PathState" not in _defs(out)
    assert "PathAction" not in _defs(out)
    ia = props["instant_answer"]
    # Collapsed to $ref or inline object — never PathState.
    assert "$ref" in ia or ia.get("type") == "object"
    start = props["path_start"]
    assert "$ref" in start or start.get("type") == "object"


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
    """Guard against grammar blow-ups (Slice 2 cycle/days + Slice 3′ hints).

    Create is split: gate (tiny) + PathState-without-plugins + hints.
    Dual-branch CREATE_RESPONSE must NOT be sent to Anthropic.
    """
    path = _anthropic_json_schema(PATH_RESPONSE_SCHEMA)
    gate = _anthropic_json_schema(CREATE_GATE_SCHEMA)
    plugins = _anthropic_json_schema(PLUGINS_MATERIALIZE_SCHEMA)
    path_m = _schema_metrics(path)
    gate_m = _schema_metrics(gate)
    plugins_m = _schema_metrics(plugins)

    # Pre-split CREATE wire was ~4.5k and failed Anthropic grammar compile.
    # Path+full plugins (~4383) still failed; Path+hints must stay well under.
    assert path_m["chars"] < 3200, path_m
    assert gate_m["chars"] < 1800, gate_m
    # Slice 4′ added stepper beats; keep well under grammar cliff (~4k+).
    assert plugins_m["chars"] < 2800, plugins_m
    assert path_m["anyOf_null"] == 0
    assert gate_m["anyOf_null"] == 0
    assert gate_m["descriptions"] == 0
    assert gate_m["chars"] < path_m["chars"]
    # Legacy dual-branch schema still exists for unit tests — must stay unused
    # for Anthropic calls (too large with plugins).
    legacy = _schema_metrics(_anthropic_json_schema(CREATE_RESPONSE_SCHEMA))
    assert legacy["chars"] > path_m["chars"]


def test_path_wire_omits_resources_milestones() -> None:
    out = _anthropic_json_schema(PATH_RESPONSE_SCHEMA)
    props = out["properties"]
    assert "resources" not in props
    assert "milestones" not in props
    assert "actions" in props
    assert "cycle" in props
    assert "days" in props


def test_path_wire_has_hints_not_plugin_objects() -> None:
    out = _anthropic_json_schema(PATH_RESPONSE_SCHEMA)
    defs = _defs(out)
    assert "PathTimer" not in defs
    assert "PathCounter" not in defs
    assert "PathClockBeat" not in defs
    assert "PathTimeline" not in defs
    assert "PathIntervalPlan" not in defs
    assert "PathStepper" not in defs
    assert "PathStepperBeat" not in defs
    action = defs["PathAction"]["properties"]
    assert "plugin_hints" in action
    assert "timers" not in action
    assert "counter" not in action
    assert "timeline" not in action
    assert "interval_plan" not in action
    assert "stepper" not in action


def test_plugins_materialize_wire_has_plugin_defs() -> None:
    out = _anthropic_json_schema(PLUGINS_MATERIALIZE_SCHEMA)
    defs = _defs(out)
    assert "PathTimer" in defs or "ActionPluginPayload" in defs
    # Payload model embeds timer/counter/timeline/stepper defs.
    payload = None
    for name, node in defs.items():
        props = (node or {}).get("properties") or {}
        if "action_id" in props and "timers" in props:
            payload = props
            break
    assert payload is not None
    assert "timers" in payload
    assert "counter" in payload
    assert "timeline" in payload
    assert "interval_plan" in payload
    assert "stepper" in payload
    assert "PathStepper" in defs or "PathStepperBeat" in defs


def test_create_gate_wire_has_no_path_branch() -> None:
    out = _anthropic_json_schema(CREATE_GATE_SCHEMA)
    props = out["properties"]
    assert "path" not in props
    assert props["kind"]["enum"] == ["path", "instant_answer"]
    assert "instant_answer" in out["required"]
    assert "path_start" in out["required"]
    assert "kind" in out["required"]
    defs = _defs(out)
    start = defs.get("PathStartSurfaceWire") or {}
    start_props = start.get("properties") or {}
    assert "paraphrase" in start_props
    assert "title" in start_props
    assert "summary" in start_props
    assert "questions" in start_props
    assert "outline_days" in start_props
    assert "actions" not in start_props
    assert "timers" not in start_props
    assert "ClarifyQuestionWire" in defs
