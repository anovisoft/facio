import type {
  ActionResponse,
  ClarifyQuestion,
  CycleResponse,
  DayResponse,
  GroupResponse,
} from '@/api/types';

/** Closed Plan Feed item kinds (Facio 0.1 Slice E2a / edit surfaces). */
export type PlanFeedItemKind =
  | 'user_turn'
  | 'sense'
  | 'plan_card'
  | 'questions'
  | 'system_note';

/** Client snapshot of a plan presentation for append-only plan cards. */
export type PlanSnapshot = {
  /** Backend state_versions id at snapshot time — used to restore before commit. */
  stateVersion: number | null;
  raw_intent: string;
  title?: string | null;
  summary?: string | null;
  outcome?: string | null;
  paraphrase?: string | null;
  success_criteria?: string | null;
  horizon?: string | null;
  domain?: string | null;
  tags: string[];
  cover_emoji?: string | null;
  cover_difficulty?: string | null;
  cover_duration_summary?: string | null;
  days: DayResponse[];
  actions: ActionResponse[];
  groups: GroupResponse[];
  cycle?: CycleResponse | null;
  pathReady: boolean;
  pathError?: string | null;
};

export type PlanFeedItem =
  | { id: string; kind: 'user_turn'; text: string }
  | { id: string; kind: 'sense'; text: string }
  | {
      id: string;
      kind: 'plan_card';
      /** 1-based display index (v1, v2…). */
      planIndex: number;
      snapshot: PlanSnapshot;
    }
  | {
      id: string;
      kind: 'questions';
      questions: ClarifyQuestion[];
      roundKey: string;
    }
  | { id: string; kind: 'system_note'; text: string };
