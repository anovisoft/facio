from __future__ import annotations

from pathlib import Path

from facio_domain.export_schema import export_schema
from facio_domain.models import Cue, Subject


def test_export_schema_writes_contract(tmp_path: Path) -> None:
    written = export_schema(tmp_path)
    names = {path.name for path in written}
    assert "subject.schema.json" in names
    assert "cue.schema.json" in names
    assert "facio.schema.json" in names
    cue_required = Cue.model_json_schema()["required"]
    assert "surface" in cue_required
    assert "delta_card.schema.json" in names
    # The old side table is gone: the ladder rides the subject now.
    assert "drift_ask_state.schema.json" not in names
    properties = Subject.model_json_schema().get("properties", {})
    # Drift itself is still derived — no `drift` field, no score, no streak.
    assert "drift" not in properties
    assert "paused_at" in properties
    # Q28 ladder memory sits next to the pause, as three plain counters.
    for field in ("drift_asks_made", "drift_retire_refusals", "drift_asked_at"):
        assert field in properties, field
    status_enum = Subject.model_json_schema()["$defs"]["SubjectStatus"]["enum"]
    assert "paused" in status_enum
