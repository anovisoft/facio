import type { ProjectDetail } from '@/api/types';

import type { PlanSnapshot } from '@/features/guide/planFeed/types';

export function isPathReady(project: ProjectDetail): boolean {
  return (
    !project.path_error &&
    project.path_ready !== false &&
    (project.actions?.length ?? 0) > 0
  );
}

export function capturePlanSnapshot(project: ProjectDetail): PlanSnapshot {
  return {
    stateVersion: project.current_version ?? null,
    raw_intent: project.raw_intent,
    title: project.title,
    summary: project.summary,
    outcome: project.outcome,
    paraphrase: project.paraphrase,
    success_criteria: project.success_criteria,
    horizon: project.horizon,
    domain: project.domain,
    tags: project.tags ?? [],
    cover_emoji: project.cover_emoji,
    cover_difficulty: project.cover_difficulty,
    cover_duration_summary: project.cover_duration_summary,
    days: project.days ?? [],
    actions: project.actions ?? [],
    groups: project.groups ?? [],
    cycle: project.cycle,
    pathReady: isPathReady(project),
    pathError: project.path_error ?? null,
  };
}

/** Fingerprint to detect “questions only” refine (no plan change). */
export function planContentFingerprint(snapshot: PlanSnapshot): string {
  const actionTitles = snapshot.actions.map((a) => a.title).join('\u0001');
  const dayTitles = snapshot.days
    .map((d) => `${d.day_index}:${d.title ?? ''}:${d.kind ?? ''}`)
    .join('\u0001');
  return [
    snapshot.title ?? '',
    snapshot.outcome ?? '',
    snapshot.paraphrase ?? '',
    snapshot.success_criteria ?? '',
    snapshot.horizon ?? '',
    dayTitles,
    actionTitles,
  ].join('\u0002');
}

export function senseText(project: ProjectDetail): string | null {
  const text = (project.paraphrase || project.outcome || '').trim();
  if (!text) return null;
  const intent = project.raw_intent.trim();
  if (intent && text.toLowerCase() === intent.toLowerCase()) return null;
  return text;
}
