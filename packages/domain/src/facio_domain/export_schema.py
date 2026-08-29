"""Dump Pydantic models to JSON Schema for the Swift client."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from facio_domain.models import (
    Cadence,
    Cue,
    DeltaCard,
    Desk,
    DriftCard,
    Instance,
    LidProjection,
    Subject,
    Target,
    Widget,
    Window,
)

_MODELS: dict[str, type] = {
    "cadence": Cadence,
    "window": Window,
    "target": Target,
    "subject": Subject,
    "cue": Cue,
    "desk": Desk,
    "instance": Instance,
    "widget": Widget,
    "drift_card": DriftCard,
    "delta_card": DeltaCard,
    "lid_projection": LidProjection,
}


def default_schema_dir() -> Path:
    here = Path(__file__).resolve()
    return here.parents[3] / "schema"


def export_schema(out_dir: Path | None = None) -> list[Path]:
    dest = out_dir or default_schema_dir()
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    combined: dict[str, object] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Facio domain",
        "$defs": {},
    }
    defs = combined["$defs"]
    assert isinstance(defs, dict)
    for name, model in _MODELS.items():
        schema = model.model_json_schema()
        path = dest / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        written.append(path)
        defs[name] = schema
    index = dest / "facio.schema.json"
    index.write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
    written.append(index)
    return written


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export Facio domain JSON Schema")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory (default: packages/schema)",
    )
    args = parser.parse_args(argv)
    for path in export_schema(args.out):
        print(path)


if __name__ == "__main__":
    main()
