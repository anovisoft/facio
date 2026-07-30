"""Anthropic JSON Schema normalization must keep fields named ``title``."""

from app.providers.anthropic_llm import _anthropic_json_schema
from app.schemas.create_response import CREATE_RESPONSE_SCHEMA
from app.schemas.path_state import PATH_RESPONSE_SCHEMA


def _defs(schema: dict) -> dict:
    return schema.get("$defs") or schema.get("definitions") or {}


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
