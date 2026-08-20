"""Subject status changes. Retire / shrink / freeze never delete instances or cues."""

from __future__ import annotations

from datetime import datetime, timedelta

from facio_domain.models import Subject, SubjectStatus

PAUSE_CHECK_IN = timedelta(days=2)


def shrink_subject(subject: Subject) -> Subject:
    return subject.model_copy(update={"status": SubjectStatus.shrunk})


def retire_subject(subject: Subject) -> Subject:
    return subject.model_copy(update={"status": SubjectStatus.retired})


def freeze_subject(subject: Subject, now: datetime) -> Subject:
    """Pause is not shrink and not retire. Cadence and target stay."""
    return subject.model_copy(update={"status": SubjectStatus.paused, "paused_at": now})


def thaw_subject(subject: Subject) -> Subject:
    return subject.model_copy(update={"status": SubjectStatus.active, "paused_at": None})


def pause_check_in_at(paused_at: datetime) -> datetime:
    return paused_at + PAUSE_CHECK_IN
