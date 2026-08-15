/** Manual TS shapes matching packages/schema. Do not call Python from the phone. */

export type CadencePeriod = 'day' | 'week' | 'none';

export type Cadence = {
  count: number | null;
  period: CadencePeriod;
};

export type Target = {
  current: number;
  goal: number;
};

export type SubjectStatus = 'active' | 'shrunk' | 'retired';

export type Subject = {
  id: string;
  title: string;
  cadence: Cadence;
  window?: { latest_by: string; closes_at: string | null } | null;
  cue_ids: string[];
  target: Target | null;
  instance_ids: string[];
  status: SubjectStatus;
};

export type CueKind = 'correction' | 'clarification';
export type CueSurface = 'do-time' | 'on-demand' | 'timing' | 'placement';

export type CueHits = {
  surfaced: number;
  applied: number;
};

export type Cue = {
  id: string;
  subject_id: string;
  step_id?: string | null;
  kind: CueKind;
  text: string;
  quote?: string | null;
  surface: CueSurface;
  hits: CueHits;
};

export type InstanceStatus = 'completed' | 'prepared' | 'in_progress';

export type Instance = {
  id: string;
  subject_id: string;
  when: string;
  status: InstanceStatus;
};

export type WidgetType = 'counter' | 'tick' | 'checklist' | 'reminder' | 'timer' | 'stepper';
export type WidgetStatus = 'ready' | 'running' | 'done' | 'skipped' | 'snoozed' | 'archived';
export type WidgetSection = 'today' | 'lifetime' | 'soon' | 'postponed';

/** Compact lid size for counter and tick. Type owns size; packer does not reorder. */
export const COMPACT_TILE = '2x2' as const;
export type TileSize = typeof COMPACT_TILE | '4x1' | '4x2' | '4x4' | '1x2' | '1x4' | '2x4' | '3x4';

export type WidgetPayload = {
  count?: number | null;
  target?: number | null;
  done?: boolean | null;
};

export type Widget = {
  id: string;
  type: WidgetType;
  title: string;
  payload: WidgetPayload;
  status: WidgetStatus;
  when: string | null;
  section: WidgetSection;
  group_id?: string | null;
  subject_id: string;
  instance_id: string;
  tile_size: TileSize;
  version: number;
};

export type RankBand =
  | 'in_progress'
  | 'overdue'
  | 'unanswered_morning'
  | 'drift_card'
  | 'soon_by_time'
  | 'today_incomplete';

export type JournalEventType =
  | 'cue_written'
  | 'cue_surfaced'
  | 'cue_applied'
  | 'instance_started'
  | 'instance_completed'
  | 'counter_ticked'
  | 'tick_toggled';

export type JournalEvent = {
  id: string;
  type: JournalEventType;
  at: string;
  subject_id?: string | null;
  widget_id?: string | null;
  instance_id?: string | null;
  cue_id?: string | null;
  payload?: Record<string, unknown> | null;
};

export type DeskSnapshot = {
  subjects: Subject[];
  cues: Cue[];
  instances: Instance[];
  widgets: Widget[];
};
