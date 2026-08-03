/**
 * Hero Preview Block kind — separate from Full Block plugin UI.
 * Order mirrors glance priority; checklist last among rich types so
 * steppers/timelines with incidental checklist rows still Hero correctly.
 */

import type { ActionResponse } from '@/api/types';

export type HeroBlockKind =
  | 'checklist'
  | 'stepper'
  | 'timeline'
  | 'timer'
  | 'fallback';

export function detectHeroBlockKind(action: ActionResponse): HeroBlockKind {
  if (action.stepper && action.stepper.beats.length > 0) return 'stepper';
  if (
    action.timeline &&
    (action.timeline.duration_sec > 0 || action.timeline.markers.length > 0)
  )
    return 'timeline';
  if (action.timers.length > 0) return 'timer';
  if (action.checklist_items.length > 0) return 'checklist';
  return 'fallback';
}
