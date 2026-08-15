"""Facio domain law — models and pure functions. No I/O, no network."""

from facio_domain.cues import add_cue, default_surface
from facio_domain.drift import (
    drift_card,
    is_drifting,
    next_drift_offer,
    silence_days,
    silence_threshold,
)
from facio_domain.lid import lid_projection, widget_rank_band
from facio_domain.models import (
    Cadence,
    Cue,
    CueKind,
    CueSurface,
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
from facio_domain.subjects import retire_subject, shrink_subject

__all__ = [
    "Cadence",
    "Cue",
    "CueKind",
    "CueSurface",
    "DriftAskState",
    "DriftCard",
    "DriftOffer",
    "Instance",
    "InstanceStatus",
    "LidProjection",
    "RankBand",
    "Subject",
    "SubjectStatus",
    "Target",
    "Widget",
    "WidgetSection",
    "WidgetStatus",
    "WidgetType",
    "Window",
    "add_cue",
    "default_surface",
    "drift_card",
    "is_drifting",
    "lid_projection",
    "next_drift_offer",
    "reminder_fire_at",
    "retire_subject",
    "shrink_subject",
    "silence_days",
    "silence_threshold",
    "widget_rank_band",
    "window_from_closing",
]
