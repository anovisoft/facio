/**
 * Focus Engine v0 (Facio 0.1 Slice B / B2) — ranking truth for Continue.
 *
 * D1 default only (13-continuity): overdue > last day > short ≤5 min > others.
 * No pin, no ML, no time-of-day / streak weights.
 *
 * Attention filter (B2): Continue lists only Sessions that need attention —
 * active Guides with executable `next_action`. Idle / waiting Guides
 * (`next_action == null`, peek-only) stay in the Guides drawer only.
 *
 * Predicates on the attention set (deterministic tiers — not opaque scores):
 *
 * 1. Overdue — next_action.day_offset < unlocked_day_index (catch-up debt).
 * 2. Last day — horizon_days > 1 AND unlocked_day_index >= horizon_days - 1
 *    (1-day Guides never get lastDay).
 * 3. Short ≤5m — next_action.estimate_min != null && estimate_min <= 5.
 * 4. Others — remaining attention candidates.
 *
 * Within each tier: updated_at descending.
 * Drafts are excluded (drawer-only).
 * Reason chip only for Focus when tier is overdue | lastDay | short.
 */

import type { ProjectSummary } from '@/api/types';

export type FocusReason = 'overdue' | 'lastDay' | 'short';

export type FocusRankResult = {
  ordered: ProjectSummary[];
  focus: ProjectSummary | null;
  reason: FocusReason | null;
};

type Tier = 0 | 1 | 2 | 3;

const TIER_OVERDUE: Tier = 0;
const TIER_LAST_DAY: Tier = 1;
const TIER_SHORT: Tier = 2;
const TIER_OTHER_EXECUTABLE: Tier = 3;

/** Active Guide with executable Session — belongs on Continue. */
export function needsAttention(p: ProjectSummary): boolean {
  return p.status === 'active' && p.next_action != null;
}

function isOverdue(p: ProjectSummary): boolean {
  const action = p.next_action;
  if (action == null) return false;
  const dayOffset = action.day_offset;
  const unlocked = p.unlocked_day_index;
  if (dayOffset == null || unlocked == null) return false;
  return dayOffset < unlocked;
}

function isLastDay(p: ProjectSummary): boolean {
  const unlocked = p.unlocked_day_index;
  const horizon = p.cycle?.horizon_days;
  if (unlocked == null || horizon == null || horizon <= 1) return false;
  return unlocked >= horizon - 1;
}

function isShortSession(p: ProjectSummary): boolean {
  const estimate = p.next_action?.estimate_min;
  return estimate != null && estimate <= 5;
}

function tierOf(p: ProjectSummary): Tier {
  if (isOverdue(p)) return TIER_OVERDUE;
  if (isLastDay(p)) return TIER_LAST_DAY;
  if (isShortSession(p)) return TIER_SHORT;
  return TIER_OTHER_EXECUTABLE;
}

function reasonFor(p: ProjectSummary): FocusReason | null {
  if (p.next_action == null) return null;
  if (isOverdue(p)) return 'overdue';
  if (isLastDay(p)) return 'lastDay';
  if (isShortSession(p)) return 'short';
  return null;
}

function byUpdatedDesc(a: ProjectSummary, b: ProjectSummary): number {
  return b.updated_at.localeCompare(a.updated_at);
}

/**
 * Rank Continue attention Sessions. Waiting Guides are filtered out before
 * ranking (drawer-only). Optional `now` reserved for future day logic;
 * v0 predicates use fields already on ProjectSummary.
 */
export function rankContinueSessions(
  projects: ProjectSummary[],
  _now?: Date,
): FocusRankResult {
  const attention = projects.filter(needsAttention);
  const sorted = [...attention].sort((a, b) => {
    const tierDiff = tierOf(a) - tierOf(b);
    if (tierDiff !== 0) return tierDiff;
    return byUpdatedDesc(a, b);
  });
  const focus = sorted[0] ?? null;
  return {
    ordered: sorted,
    focus,
    reason: focus ? reasonFor(focus) : null,
  };
}
