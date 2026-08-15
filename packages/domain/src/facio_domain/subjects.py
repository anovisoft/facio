"""Subject status changes. Retire / shrink never delete instances or cues."""

from __future__ import annotations

from facio_domain.models import Subject, SubjectStatus


def shrink_subject(subject: Subject) -> Subject:
    return subject.model_copy(update={"status": SubjectStatus.shrunk})


def retire_subject(subject: Subject) -> Subject:
    return subject.model_copy(update={"status": SubjectStatus.retired})
