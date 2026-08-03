import type { ActionResponse } from '@/api/types';

/** Rough UI Block type glance for Continue cards (Slice A — no Cover polish). */
export function blockTypeLabel(action: ActionResponse | null | undefined): string | null {
  if (!action) return null;
  if (action.stepper) return 'Stepper';
  if (action.timeline) return 'Timeline';
  if (action.interval_plan) return 'Intervals';
  if (action.timers.length > 0) return 'Timer';
  if (action.counter) return 'Counter';
  if (action.checklist_items.length > 0) return 'Checklist';
  if (action.plugin_hints && action.plugin_hints.length > 0) {
    return action.plugin_hints[0] ?? null;
  }
  return null;
}
