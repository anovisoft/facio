import type { ActionResponse, DayResponse } from '@/api/types';

export type CompactRoadmapStatus = 'pending' | 'done' | 'skipped' | 'locked';

export type CompactRoadmapRow = {
  key: string;
  /** Set when this row opens a new day group (multi-day Guides). */
  dayIndex?: number | null;
  dayTitle?: string | null;
  title: string;
  status: CompactRoadmapStatus;
};

/**
 * Compact Summary rows for Guide roadmap — title + status mark per Session.
 * Not Full Block; not PathList dump. Groups by day when days exist.
 */
export function buildCompactRoadmap(
  actions: ActionResponse[],
  days: DayResponse[],
): CompactRoadmapRow[] {
  if (actions.length === 0) return [];

  const sortedActions = [...actions].sort((a, b) => {
    const dayA = a.day_offset ?? 0;
    const dayB = b.day_offset ?? 0;
    if (dayA !== dayB) return dayA - dayB;
    return a.sort - b.sort;
  });

  const dayByIndex = new Map(days.map((d) => [d.day_index, d]));
  const multiDay =
    days.length > 1 || sortedActions.some((a) => (a.day_offset ?? 0) > 0);

  const rows: CompactRoadmapRow[] = [];
  let lastDay: number | null = null;

  for (const action of sortedActions) {
    const dayIndex = action.day_offset ?? 0;
    let sectionDayIndex: number | null = null;
    let sectionDayTitle: string | null = null;
    if (multiDay && dayIndex !== lastDay) {
      const day = dayByIndex.get(dayIndex);
      sectionDayIndex = dayIndex;
      sectionDayTitle = day?.title ?? null;
      lastDay = dayIndex;
    }

    rows.push({
      key: action.id,
      dayIndex: sectionDayIndex,
      dayTitle: sectionDayTitle,
      title: action.title,
      status: roadmapStatus(action),
    });
  }

  return rows;
}

function roadmapStatus(action: ActionResponse): CompactRoadmapStatus {
  switch (action.status) {
    case 'done':
      return 'done';
    case 'skipped':
      return 'skipped';
    case 'pending':
      return action.day_locked ? 'locked' : 'pending';
    default: {
      const _exhaustive: never = action.status;
      return _exhaustive;
    }
  }
}
