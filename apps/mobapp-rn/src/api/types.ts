/** Hand-written types mirroring client-service `app/schemas/api.py`. */

export type ProjectStatus = 'draft' | 'active' | 'abandoned' | 'completed';

export type ActionStatus = 'pending' | 'done' | 'skipped';

export type DayKind = 'train' | 'rest' | 'cook_session' | 'other';

export type CycleStatus = 'draft' | 'active' | 'completed' | 'abandoned';

export type ListStatusFilter =
  | 'open'
  | 'abandoned'
  | 'draft'
  | 'active'
  | 'completed';

export type FirstStepWhen = 'today' | 'tomorrow';

export type RepairIntent = 'shift' | 'lighten' | 'rest';

export type ContinueKind = 'next' | 'repeat';

export interface CycleResultResponse {
  completed_steps: number;
  skipped_steps: number;
  pending_steps?: number;
  partial?: boolean;
  partial_notes?: string | null;
  counters_snapshot?: Array<Record<string, unknown>>;
  user_comment?: string | null;
  finished_at?: string | null;
}

export interface CycleHistoryEntry {
  index: number;
  horizon_days: number;
  goal_for_cycle?: string | null;
  title?: string | null;
  summary?: string | null;
  cycle_result?: CycleResultResponse | null;
  path_snapshot?: Record<string, unknown> | null;
  completed_at?: string | null;
}

export type ClientBeaconType =
  | 'app_opened'
  | 'accept_viewed'
  | 'action_shown'
  | 'path_opened'
  | 'project_switched';

export interface ClarifyQuestion {
  id: string;
  prompt: string;
  options: string[];
}

export interface RefineAnswerItem {
  question_id: string;
  value: string;
}

export interface ChecklistItemResponse {
  id: string;
  action_id: string;
  key?: string | null;
  title: string;
  done: boolean;
  sort: number;
}

export type TimerSignal = 'nudge' | 'alert';

export interface TimerResponse {
  id: string;
  title: string;
  duration_sec: number;
  signal: TimerSignal;
  parallel_group?: string | null;
  completed: boolean;
}

export interface CounterResponse {
  label?: string | null;
  target: number;
  current: number;
  step: number;
}

export interface TimelineMarkerResponse {
  at_sec: number;
  title: string;
  signal: TimerSignal;
}

export interface ActionTimelineResponse {
  duration_sec: number;
  markers: TimelineMarkerResponse[];
}

export interface IntervalSegmentResponse {
  duration_sec: number;
  title: string;
  signal: TimerSignal;
}

export interface IntervalPlanResponse {
  segments: IntervalSegmentResponse[];
}

export type StepperBeatKind = 'measure' | 'work' | 'rest';

export interface StepperBeatResponse {
  id: string;
  kind: StepperBeatKind;
  title: string;
  counter?: CounterResponse | null;
  duration_sec?: number | null;
  signal?: TimerSignal | null;
}

export interface StepperResponse {
  beats: StepperBeatResponse[];
}

export interface GroupResponse {
  id: string;
  key: string;
  title: string;
  description?: string | null;
  sort: number;
}

export interface CycleResponse {
  index: number;
  horizon_days: number;
  status: CycleStatus | string;
  goal_for_cycle?: string | null;
}

export interface DayResponse {
  day_index: number;
  kind: DayKind;
  title?: string | null;
  summary?: string | null;
}

export interface CurrentDayResponse {
  day_index: number;
  day_number: number;
  horizon_days: number;
  kind: DayKind;
  title?: string | null;
  summary?: string | null;
}

export interface ActionResponse {
  id: string;
  project_id: string;
  key?: string | null;
  title: string;
  why: string;
  detail?: string | null;
  estimate_min?: number | null;
  due_at?: string | null;
  sort: number;
  status: ActionStatus;
  day_offset?: number | null;
  /**
   * True when day_offset is beyond the physical-day unlock window
   * (docs/next/04 §4). Preview only — complete/skip/plugin mutations are
   * rejected server-side (409) while locked.
   */
  day_locked?: boolean;
  group_id?: string | null;
  group_key?: string | null;
  group_title?: string | null;
  checklist_items: ChecklistItemResponse[];
  /** Create #2 tool announcements; full plugins arrive after Start. */
  plugin_hints?: string[];
  timers: TimerResponse[];
  counter?: CounterResponse | null;
  timeline?: ActionTimelineResponse | null;
  interval_plan?: IntervalPlanResponse | null;
  stepper?: StepperResponse | null;
}

export interface ProjectSummary {
  id: string;
  status: ProjectStatus;
  raw_intent: string;
  title?: string | null;
  summary?: string | null;
  outcome?: string | null;
  paraphrase?: string | null;
  success_criteria?: string | null;
  horizon?: string | null;
  domain?: string | null;
  tags: string[];
  cycle?: CycleResponse | null;
  current_day?: CurrentDayResponse | null;
  committed_at?: string | null;
  created_at: string;
  updated_at: string;
  /**
   * Current «Сегодня» step: earliest pending action with
   * day_offset <= unlocked_day_index (physical-day focus). Null for
   * draft / completed / abandoned, or while waiting for the next
   * calendar day (see peek_action).
   */
  next_action?: ActionResponse | null;
  /** clamp(local_today - cycle_anchor_date, 0..horizon_days-1). Null for non-active projects. */
  /** Execute ceiling: -1 before cycle_anchor_date; else min(delta, horizon-1). */
  unlocked_day_index?: number | null;
  /** Calendar date day_offset=0 unlocked (commit date, +1 when first_step_when=tomorrow). */
  cycle_anchor_date?: string | null;
  /**
   * Read-only preview of the next locked action when there is no
   * executable next_action today (day done early / waiting on calendar).
   * Never completable — day_locked is always true.
   */
  peek_action?: ActionResponse | null;
  /** Day framing for peek_action, when present. */
  peek_day?: CurrentDayResponse | null;
  /** Calendar date peek_action becomes executable, when waiting. */
  next_unlock_date?: string | null;
}

export interface ProjectDetail extends ProjectSummary {
  groups: GroupResponse[];
  days: DayResponse[];
  actions: ActionResponse[];
  questions: ClarifyQuestion[];
  resources: string[];
  milestones: string[];
  current_version?: number | null;
  /** False while progressive create phase-2 Path skeleton is still generating. */
  path_ready?: boolean;
  /** Set when phase-2 failed — stop polling, show error. */
  path_error?: string | null;
  /** False while phase-3 plugin materialize runs after Start. */
  plugins_ready?: boolean;
  /** Set when phase-3 failed — stop polling, show error + retry. */
  plugins_error?: string | null;
  /**
   * Set only on the response to POST .../repair: short one-line "what
   * changed" summary for a confirmation toast/banner. Not present on GET.
   */
  repair_summary?: string | null;
  /** Structured summary when the current cycle is finished. */
  cycle_result?: CycleResultResponse | null;
  /** Archived prior cycles (lean) — cycle 1 stays visible. */
  cycles_history?: CycleHistoryEntry[];
  /** True when N+1 / Repeat CTA may show. */
  next_cycle_available?: boolean;
  /** True when user may close early via «Завершить цикл». */
  can_finish_cycle?: boolean;
  /** 'repeat' for cook/horizon=1; 'next' for multi-day. */
  continue_kind?: ContinueKind | null;
  /** Optional model-provided CTA subtitle (copy only). */
  continue_label?: string | null;
}

export interface InstantAnswerResponse {
  kind: 'instant_answer';
  label: string;
  answer: string;
  goal_suggestions: string[];
  raw_intent: string;
  llm_call_id: string;
  event_id?: string | null;
  domain?: string | null;
}

export interface PathCreatedResponse {
  kind: 'path';
  project: ProjectDetail;
}

export type CreateIntentResponse = InstantAnswerResponse | PathCreatedResponse;

export interface StateVersionSummary {
  version: number;
  source: string;
  created_at: string;
}

export interface EventResponse {
  id: string;
  type: string;
  user_id?: string | null;
  project_id?: string | null;
  payload?: Record<string, unknown> | null;
  created_at: string;
}

export interface ApiErrorBody {
  detail?: string | { msg?: string }[] | Record<string, unknown>;
}

export class ApiError extends Error {
  readonly status: number;
  readonly body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}
