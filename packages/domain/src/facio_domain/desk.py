"""Founding desk for talk goldens. Fixtures plus the instances widgets already name."""

from __future__ import annotations

from datetime import datetime, timedelta

from facio_domain.fixtures import load_cues, load_subjects, load_widgets
from facio_domain.models import Desk, Instance, InstanceStatus, Subject


def founding_desk(*, now: datetime | None = None) -> Desk:
    """A desk the goldens can mutate. Same ids as `packages/domain/fixtures`."""
    stamp = now or datetime(2026, 8, 15, 12, 0, 0)
    subjects = [subject.model_copy(deep=True) for subject in load_subjects()]
    widgets = [widget.model_copy(deep=True) for widget in load_widgets()]
    cues = [cue.model_copy(deep=True) for cue in load_cues()]
    instances = [
        Instance(id="push-ups-open", subject_id="push-ups", when=stamp, status=InstanceStatus.prepared),
        Instance(id="bike-open", subject_id="bike", when=stamp.replace(hour=19, minute=0), status=InstanceStatus.prepared),
        Instance(
            id="bike-silent",
            subject_id="bike",
            when=stamp - timedelta(days=21),
            status=InstanceStatus.completed,
        ),
        Instance(id="vegetables-open", subject_id="vegetables", when=stamp, status=InstanceStatus.prepared),
    ]
    by_id = {subject.id: subject for subject in subjects}
    _bind_instances(by_id["push-ups"], ["push-ups-open"])
    _bind_instances(by_id["bike"], ["bike-open", "bike-silent"])
    _bind_instances(by_id["vegetables"], ["vegetables-open"])
    return Desk(
        subjects=list(by_id.values()),
        cues=cues,
        instances=instances,
        widgets=widgets,
    )


def _bind_instances(subject: Subject, ids: list[str]) -> None:
    for instance_id in ids:
        if instance_id not in subject.instance_ids:
            subject.instance_ids.append(instance_id)
