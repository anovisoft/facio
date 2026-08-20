"""Facio domain law — models and pure functions. No I/O, no network."""

from facio_domain.cues import add_cue, default_surface
from facio_domain.desk import founding_desk
from facio_domain.pain import reports_pain
from facio_domain.tools import apply_tool, snapshot_cards, times_per_week
from facio_domain.drift import (
    drift_card,
    is_drifting,
    next_drift_offer,
    silence_days,
    silence_threshold,
)
from facio_domain.lid import lid_projection, widget_rank_band
from facio_domain.slots import DayStrip, Horizon, Slot, SlotKind, slot_horizon
from facio_domain.models import (
    Cadence,
    Cue,
    CueKind,
    CueSurface,
    Desk,
    DriftAskState,
    DriftCard,
    DriftOffer,
    Instance,
    InstanceStatus,
    LidProjection,
    RankBand,
    Subject,
    SubjectStatus,
    Target,
    Widget,
    WidgetSection,
    WidgetStatus,
    WidgetType,
    Window,
)
from facio_domain.reminder import reminder_fire_at, window_from_closing
from facio_domain.subjects import (
    freeze_subject,
    pause_check_in_at,
    retire_subject,
    shrink_subject,
    thaw_subject,
)

__all__ = [
    "Cadence",
    "Cue",
    "CueKind",
    "CueSurface",
    "DayStrip",
    "Desk",
    "DriftAskState",
    "DriftCard",
    "DriftOffer",
    "Horizon",
    "Instance",
    "InstanceStatus",
    "LidProjection",
    "RankBand",
    "Slot",
    "SlotKind",
    "Subject",
    "SubjectStatus",
    "Target",
    "Widget",
    "WidgetSection",
    "WidgetStatus",
    "WidgetType",
    "Window",
    "add_cue",
    "apply_tool",
    "default_surface",
    "founding_desk",
    "freeze_subject",
    "pause_check_in_at",
    "reports_pain",
    "snapshot_cards",
    "times_per_week",
    "drift_card",
    "is_drifting",
    "lid_projection",
    "next_drift_offer",
    "reminder_fire_at",
    "retire_subject",
    "shrink_subject",
    "thaw_subject",
    "silence_days",
    "silence_threshold",
    "slot_horizon",
    "widget_rank_band",
    "window_from_closing",
]
