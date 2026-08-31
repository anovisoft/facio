"""Time-travel: show what the lid/slots look like for a desk at a given `now`.

Ad-hoc exploration tool, not a test. Reads a `Desk` JSON (stdin or --file),
shifts `now`, and prints the resulting lid projection and 7-day slot horizon —
so a drift card or a cadence-day question can be checked by hand without
waiting real days or standing up a database.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from facio_domain.lid import lid_projection
from facio_domain.models import Desk
from facio_domain.slots import slot_horizon


def _resolve_now(args: argparse.Namespace) -> datetime:
    if args.now:
        return datetime.fromisoformat(args.now)
    base = datetime.fromisoformat(args.base) if args.base else datetime.now()
    return base + timedelta(days=args.days)


def _load_desk(args: argparse.Namespace) -> Desk:
    raw = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    return Desk.model_validate(json.loads(raw))


def render(desk: Desk, now: datetime) -> dict[str, Any]:
    lid = lid_projection(
        now,
        desk.subjects,
        desk.instances,
        desk.widgets,
    )
    horizon = slot_horizon(desk, origin=now.date())
    return {
        "now": now.isoformat(),
        "today": [
            item.drift_card.model_dump(mode="json")
            if item.kind == "drift"
            else item.delta_card.model_dump(mode="json")
            if item.kind == "delta"
            else {
                "band": item.band,
                "widget_id": item.widget.id,
                "title": item.widget.title,
                "subject_id": item.widget.subject_id,
            }
            for item in lid.today
        ],
        "lifetime": [w.id for w in lid.lifetime],
        "soon": [w.id for w in lid.soon],
        "postponed": [w.id for w in lid.postponed],
        "drift_card": lid.drift_card.model_dump(mode="json") if lid.drift_card else None,
        "delta_card": lid.delta_card.model_dump(mode="json") if lid.delta_card else None,
        "horizon": horizon.model_dump(mode="json"),
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Show lid + 7-day slot horizon for a desk JSON at a shifted `now`."
    )
    parser.add_argument("--file", type=Path, default=None, help="Desk JSON file (default: stdin)")
    parser.add_argument("--now", default=None, help="Absolute ISO datetime for `now`")
    parser.add_argument(
        "--base", default=None, help="Base ISO datetime for --days (default: real now)"
    )
    parser.add_argument("--days", type=int, default=0, help="Offset in days added to --base")
    args = parser.parse_args(argv)

    desk = _load_desk(args)
    now = _resolve_now(args)
    print(json.dumps(render(desk, now), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
