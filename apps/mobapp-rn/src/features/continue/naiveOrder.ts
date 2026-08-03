import type { ProjectSummary } from '@/api/types';

/**
 * Slice A — naive Continue order (NOT Focus Engine).
 *
 * Stable rule for dogfood until Slice B:
 * 1. Active Guides with an executable `next_action` first
 * 2. Then other active Guides (waiting / peek-only)
 * 3. Within each bucket: `updated_at` descending
 *
 * Drafts are excluded from Continue (drawer only).
 * Focus Engine weighted ranking (D1: overdue > last day > short ≤5m > …)
 * lands in Slice B — do not invent weights here.
 */
export function orderContinueSessions(
  projects: ProjectSummary[],
): ProjectSummary[] {
  const active = projects.filter((p) => p.status === 'active');
  const withSession = active.filter((p) => p.next_action != null);
  const waiting = active.filter((p) => p.next_action == null);

  const byUpdatedDesc = (a: ProjectSummary, b: ProjectSummary) =>
    b.updated_at.localeCompare(a.updated_at);

  return [
    ...withSession.sort(byUpdatedDesc),
    ...waiting.sort(byUpdatedDesc),
  ];
}
