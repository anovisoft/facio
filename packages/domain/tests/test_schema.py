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
    assert "drift" not in Subject.model_json_schema().get("properties", {})
