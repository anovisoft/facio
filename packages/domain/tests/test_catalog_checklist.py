"""Checklist as a practice, not a to-do list (Q1, never-do #14).

The type ships only if all four hold on it exactly as they hold on the
counter: a rhythm it was created with, a do-time cue that reaches the tile,
drift when the rhythm is missed, and a finished instance that leaves Today.
Everything below is one of those four, or the line ticking underneath them.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from facio_domain.desk import founding_desk
from facio_domain.drift import drift_card
from facio_domain.lid import lid_projection
from facio_domain.models import (
    Cadence,
    ChecklistItem,
    Desk,
    Instance,
    InstanceStatus,
    Subject,
    Widget,
    WidgetPayload,
    WidgetSection,
    WidgetStatus,
    WidgetType,
)
from facio_domain.morning import morning_delta
from facio_domain.runtime import (
    build_checklist_items,
    checklist_is_done,
    checklist_progress,
    set_checklist_done,
    toggle_checklist_item,
)
from facio_domain.tools import CADENCE_REQUIRED, INVALID_ITEMS, apply_tool, snapshot_cards

NOW = datetime(2026, 8, 15, 12, 0, 0)
GROCERIES = ["хлеб", "молоко", "яблоки"]


def _apply(desk: Desk, name: str, arguments: dict, *, pain: bool = False):
    return apply_tool(desk, name, arguments, pain=pain, now=NOW)


def _create(desk: Desk, **overrides):
    args = {
        "type": "checklist",
        "title": "список покупок",
        "subject_id": "groceries",
        "cadence": {"count": 1, "period": "week"},
        "items": GROCERIES,
    }
    args.update(overrides)
    return _apply(desk, "create_widget", args)


def _widget(desk: Desk, subject_id: str) -> Widget:
    return next(row for row in desk.widgets if row.subject_id == subject_id)


def _subject(desk: Desk, subject_id: str) -> Subject:
    return next(row for row in desk.subjects if row.id == subject_id)


# --- it lands, and it lands with a rhythm ---------------------------------


def test_a_checklist_lands_with_its_lines_its_rhythm_and_its_size() -> None:
    outcome = _create(founding_desk(now=NOW))
    assert outcome.ok is True
    assert outcome.mutated is True
    widget = _widget(outcome.desk, "groceries")
    assert widget.type == WidgetType.checklist
    assert [item.text for item in widget.payload.items or []] == GROCERIES
    assert all(item.done is False for item in widget.payload.items or [])
    # Type owns the shape (never-do #8), out of Q18's preferred set. Without a
    # size the packer would give it the default cell and the row would gap.
    assert widget.tile_size == "4x2"
    assert widget.section == WidgetSection.today
    subject = _subject(outcome.desk, "groceries")
    assert subject.cadence == Cadence.of(1, "week")


def test_a_checklist_on_a_new_subject_still_needs_a_rhythm() -> None:
    """`cadence_required` (R0) is not relaxed for the new types."""
    desk = founding_desk(now=NOW)
    outcome = _create(desk, cadence=None)
    assert outcome.ok is False
    assert outcome.error == CADENCE_REQUIRED
    assert outcome.desk is desk
    assert "groceries" not in {row.id for row in outcome.desk.subjects}


def test_a_checklist_with_no_lines_does_not_land() -> None:
    """An empty list is an empty tile — nothing to tick, nothing to finish."""
    desk = founding_desk(now=NOW)
    widget_count = len(desk.widgets)
    for items in ([], None, "хлеб, молоко", [""], [{"done": True}]):
        outcome = _create(desk, items=items)
        assert outcome.ok is False, items
        assert outcome.error == INVALID_ITEMS, items
        assert outcome.desk is desk
        assert len(outcome.desk.widgets) == widget_count
        assert "groceries" not in {row.id for row in outcome.desk.subjects}


def test_items_arrive_as_text_or_as_rows() -> None:
    built = build_checklist_items(["хлеб", {"text": "молоко", "done": True}])
    assert built is not None
    assert [item.text for item in built] == ["хлеб", "молоко"]
    assert [item.done for item in built] == [False, True]
    # Ids are filled in positionally: a finger tick has to address one row.
    assert len({item.id for item in built}) == 2


# --- ticking a line is arithmetic, and it is pure -------------------------


def test_progress_is_counted_and_never_stored() -> None:
    payload = WidgetPayload(items=build_checklist_items(GROCERIES))
    assert checklist_progress(payload) == (0, 3)
    ticked = toggle_checklist_item(payload, "item-2")
    assert checklist_progress(ticked) == (1, 3)
    assert checklist_is_done(ticked) is False
    # The original is untouched: these are pure functions over a payload.
    assert checklist_progress(payload) == (0, 3)
    # And there is no «progress» key anywhere near the payload.
    assert "progress" not in ticked.model_dump()


def test_ticking_twice_puts_the_line_back() -> None:
    payload = WidgetPayload(items=build_checklist_items(GROCERIES))
    once = toggle_checklist_item(payload, "item-1")
    twice = toggle_checklist_item(once, "item-1")
    assert twice.items == payload.items


def test_a_line_that_is_not_there_changes_nothing() -> None:
    payload = WidgetPayload(items=build_checklist_items(GROCERIES))
    assert toggle_checklist_item(payload, "item-9") == payload


def test_an_empty_list_is_not_done() -> None:
    assert checklist_is_done(WidgetPayload(items=[])) is False
    assert checklist_is_done(WidgetPayload()) is False
    assert set_checklist_done(WidgetPayload(), True) == WidgetPayload()


def test_every_line_ticked_is_done() -> None:
    payload = set_checklist_done(WidgetPayload(items=build_checklist_items(GROCERIES)), True)
    assert checklist_is_done(payload) is True
    assert checklist_progress(payload) == (3, 3)


# --- complete / skip -------------------------------------------------------


def test_complete_finishes_every_line_and_closes_the_instance() -> None:
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "groceries")
    outcome = _apply(created.desk, "complete", {"widget_id": widget.id})
    assert outcome.ok is True
    done = _widget(outcome.desk, "groceries")
    assert done.status == WidgetStatus.done
    assert checklist_is_done(done.payload) is True
    instance = next(row for row in outcome.desk.instances if row.id == done.instance_id)
    assert instance.status == InstanceStatus.completed


def test_skip_leaves_the_lines_alone() -> None:
    """A skipped day is not a finished list — the ticks stay where they were."""
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "groceries")
    outcome = _apply(created.desk, "skip", {"widget_id": widget.id})
    skipped = _widget(outcome.desk, "groceries")
    assert skipped.status == WidgetStatus.skipped
    assert checklist_progress(skipped.payload) == (0, 3)


def test_restructuring_the_list_goes_through_update_widget() -> None:
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "groceries")
    outcome = _apply(
        created.desk,
        "update_widget",
        {"widget_id": widget.id, "items": ["хлеб", "молоко", "яблоки", "кофе"]},
    )
    assert outcome.ok is True
    assert checklist_progress(_widget(outcome.desk, "groceries").payload) == (0, 4)


def test_a_counter_does_not_take_checklist_lines() -> None:
    desk = founding_desk(now=NOW)
    outcome = _apply(desk, "update_widget", {"widget_id": "push-ups-counter", "items": ["раз"]})
    assert outcome.ok is False
    assert outcome.error == INVALID_ITEMS
    assert outcome.desk is desk


# --- the cue reaches it, the drift counts it ------------------------------


def test_the_do_time_cue_rides_the_checklist_snapshot() -> None:
    """A widget bound to a subject renders that subject's do-time cues (04)."""
    created = _create(founding_desk(now=NOW))
    widget = _widget(created.desk, "groceries")
    with_cue = _apply(
        created.desk,
        "add_cue",
        {
            "subject_id": "groceries",
            "kind": "correction",
            "text": "иди после работы, не голодным",
            "surface": "do-time",
        },
    )
    assert with_cue.ok is True
    card = snapshot_cards(with_cue.desk, [widget.id])[0]
    assert card["line"].startswith("0 / 3")
    assert "иди после работы, не голодным" in card["line"]
    # A picture, not a runtime (never-do #6): the card carries no tickable row.
    assert "items" not in card


def test_a_quiet_checklist_drifts_like_any_other_practice() -> None:
    subject = Subject(
        id="groceries",
        title="список покупок",
        cadence=Cadence.of(1, "week"),
        instance_ids=["groceries-old"],
    )
    instances = [
        Instance(
            id="groceries-old",
            subject_id="groceries",
            when=NOW - timedelta(days=21),
            status=InstanceStatus.completed,
        )
    ]
    card = drift_card([subject], instances, NOW)
    assert card is not None
    assert card.subject_id == "groceries"
    assert card.silent_days == 21


def test_the_checklist_rhythm_is_counted_in_the_morning_delta() -> None:
    subject = Subject(
        id="groceries",
        title="список покупок",
        cadence=Cadence.of(2, "week"),
        instance_ids=["groceries-done"],
    )
    instances = [
        Instance(
            id="groceries-done",
            subject_id="groceries",
            when=NOW - timedelta(days=1),
            status=InstanceStatus.completed,
        )
    ]
    assert morning_delta(subject, instances, NOW) == 1


# --- done leaves Today -----------------------------------------------------


@pytest.mark.parametrize(
    ("when", "on_today"),
    [
        pytest.param(NOW, True, id="done-today-stays-dim"),
        pytest.param(NOW - timedelta(days=1), False, id="done-yesterday-is-gone"),
    ],
)
def test_a_finished_checklist_leaves_today_with_the_day(when: datetime, on_today: bool) -> None:
    subject = Subject(id="groceries", title="список покупок", cadence=Cadence.of(1, "week"))
    widget = Widget(
        id="groceries-list",
        type=WidgetType.checklist,
        title="список покупок",
        payload=WidgetPayload(items=[ChecklistItem(id="item-1", text="хлеб", done=True)]),
        status=WidgetStatus.done,
        when=when,
        section=WidgetSection.today,
        subject_id="groceries",
        instance_id="groceries-open",
    )
    projection = lid_projection(NOW, [subject], [], [widget])
    ids = [item.widget.id for item in projection.today if item.kind == "widget"]
    assert (widget.id in ids) is on_today
