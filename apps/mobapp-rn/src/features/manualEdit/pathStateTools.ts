/**
 * PathState tool-field helpers for Manual editor (Slice E2b).
 * Mutates closed UI Block fields on PathState JSON — not raw free-form authoring.
 */

export type PathStateJson = {
  actions?: PathActionJson[];
  [key: string]: unknown;
};

export type PathChecklistItemJson = {
  id?: string | null;
  title: string;
  done?: boolean;
  sort?: number;
};

export type PathCounterJson = {
  label?: string | null;
  target: number;
  current?: number;
  step?: number;
};

export type PathStepperBeatJson = {
  id?: string | null;
  kind: 'measure' | 'work' | 'rest' | string;
  title: string;
  counter?: PathCounterJson | null;
  duration_sec?: number | null;
  signal?: string | null;
};

export type PathStepperJson = {
  beats: PathStepperBeatJson[];
};

export type PathTimerJson = {
  id?: string | null;
  title: string;
  duration_sec: number;
  signal: string;
  parallel_group?: string | null;
};

export type PathTimelineJson = {
  duration_sec: number;
  markers: Array<{ sec: number; title: string; signal: string }>;
};

export type PathIntervalJson = {
  segments: Array<{ sec: number; title: string; signal: string }>;
};

export type PathActionJson = {
  id?: string | null;
  title: string;
  why?: string;
  checklist_items?: PathChecklistItemJson[];
  counter?: PathCounterJson | null;
  stepper?: PathStepperJson | null;
  timers?: PathTimerJson[];
  timeline?: PathTimelineJson | null;
  interval_plan?: PathIntervalJson | null;
  plugin_hints?: string[];
  [key: string]: unknown;
};

/** Editable draft of one action's tools — UI working copy. */
export type EditableActionTools = {
  actionId: string;
  title: string;
  checklistItems: PathChecklistItemJson[];
  counter: PathCounterJson | null;
  stepper: PathStepperJson | null;
  timers: PathTimerJson[];
  timeline: PathTimelineJson | null;
  intervalPlan: PathIntervalJson | null;
  /** True when only plugin_hints announce tools (no payloads yet). */
  hintsOnly: boolean;
  pluginHints: string[];
};

function hasToolPayload(action: PathActionJson): boolean {
  return (
    (action.checklist_items?.length ?? 0) > 0 ||
    action.counter != null ||
    action.stepper != null ||
    (action.timers?.length ?? 0) > 0 ||
    action.timeline != null ||
    action.interval_plan != null
  );
}

export function extractEditableActions(
  state: PathStateJson,
  actionKeyFilter?: string | null,
): EditableActionTools[] {
  const actions = state.actions ?? [];
  const out: EditableActionTools[] = [];
  for (const action of actions) {
    const id = action.id ?? '';
    if (!id) continue;
    if (actionKeyFilter && id !== actionKeyFilter) continue;
    if (!hasToolPayload(action) && !(action.plugin_hints?.length ?? 0)) {
      continue;
    }
    const hintsOnly =
      !hasToolPayload(action) && (action.plugin_hints?.length ?? 0) > 0;
    out.push({
      actionId: id,
      title: action.title,
      checklistItems: (action.checklist_items ?? []).map((c, i) => ({
        id: c.id ?? `c${i}`,
        title: c.title,
        done: c.done ?? false,
        sort: c.sort ?? i,
      })),
      counter: action.counter
        ? {
            label: action.counter.label ?? null,
            target: action.counter.target,
            current: action.counter.current ?? 0,
            step: action.counter.step ?? 1,
          }
        : null,
      stepper: action.stepper
        ? {
            beats: action.stepper.beats.map((b, i) => ({
              ...b,
              id: b.id ?? `b${i}`,
            })),
          }
        : null,
      timers: (action.timers ?? []).map((t, i) => ({
        ...t,
        id: t.id ?? `t${i}`,
      })),
      timeline: action.timeline ?? null,
      intervalPlan: action.interval_plan ?? null,
      hintsOnly,
      pluginHints: action.plugin_hints ?? [],
    });
  }
  return out;
}

/** Write edited tool fields back onto a deep-cloned PathState. */
export function applyEditableActionsToState(
  state: PathStateJson,
  edits: EditableActionTools[],
): PathStateJson {
  const byId = new Map(edits.map((e) => [e.actionId, e]));
  const actions = (state.actions ?? []).map((action) => {
    const id = action.id ?? '';
    const edit = byId.get(id);
    if (!edit) return action;
    return {
      ...action,
      checklist_items: edit.checklistItems.map((c, i) => ({
        id: c.id ?? `c${i}`,
        title: c.title.trim(),
        done: c.done ?? false,
        sort: c.sort ?? i,
      })),
      counter: edit.counter
        ? {
            label: edit.counter.label?.trim() || null,
            target: Math.max(1, Math.floor(edit.counter.target) || 1),
            current: Math.max(0, Math.floor(edit.counter.current ?? 0)),
            step: Math.max(1, Math.floor(edit.counter.step ?? 1)),
          }
        : null,
      stepper: edit.stepper
        ? {
            beats: edit.stepper.beats.map((b, i) => {
              const kind = b.kind;
              const base = {
                id: b.id ?? `b${i}`,
                kind,
                title: b.title.trim() || `Beat ${i + 1}`,
                signal: b.signal ?? null,
              };
              if (kind === 'rest') {
                return {
                  ...base,
                  counter: null,
                  duration_sec: Math.max(
                    1,
                    Math.floor(b.duration_sec ?? 60) || 60,
                  ),
                };
              }
              return {
                ...base,
                duration_sec: null,
                counter: {
                  label: b.counter?.label?.trim() || null,
                  target: Math.max(1, Math.floor(b.counter?.target ?? 1) || 1),
                  current: Math.max(0, Math.floor(b.counter?.current ?? 0)),
                  step: Math.max(1, Math.floor(b.counter?.step ?? 1) || 1),
                },
              };
            }),
          }
        : null,
      timers: edit.timers.map((t, i) => ({
        id: t.id ?? `t${i}`,
        title: t.title.trim() || `Timer ${i + 1}`,
        duration_sec: Math.max(1, Math.floor(t.duration_sec) || 1),
        signal: t.signal || 'nudge',
        parallel_group: t.parallel_group ?? null,
      })),
      timeline: edit.timeline
        ? {
            duration_sec: Math.max(
              1,
              Math.floor(edit.timeline.duration_sec) || 1,
            ),
            markers: edit.timeline.markers.map((m) => ({
              sec: Math.max(0, Math.floor(m.sec) || 0),
              title: m.title.trim() || 'Marker',
              signal: m.signal || 'nudge',
            })),
          }
        : null,
      interval_plan: edit.intervalPlan
        ? {
            segments: edit.intervalPlan.segments.map((s) => ({
              sec: Math.max(1, Math.floor(s.sec) || 1),
              title: s.title.trim() || 'Segment',
              signal: s.signal || 'nudge',
            })),
          }
        : null,
    };
  });
  return { ...state, actions };
}

let checklistSeq = 0;
export function newChecklistItemId(): string {
  checklistSeq += 1;
  return `manual-c-${Date.now()}-${checklistSeq}`;
}
