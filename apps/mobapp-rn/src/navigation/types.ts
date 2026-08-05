import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { InstantAnswerResponse, ProjectDetail } from '@/api/types';

/**
 * Facio 0.1 IA routes (Slice A+C).
 * Prototype aliases: Continue←Projects, Session←ProjectHome,
 * Guide←Path/DraftStudio (unified trust surface), Create←Intent, Archive←History.
 * GuideExplore stays as a thin alias of Guide (same screen, optional seed).
 * InstantAnswer stays typed/registered but is off the Create happy path (D5).
 */
export type RootStackParamList = {
  Continue: undefined;
  Create: undefined;
  /** Dead route — not linked from Create (D5). Screen kept for now. */
  InstantAnswer: { payload: InstantAnswerResponse };
  /**
   * Alias of Guide for Create soft-start with seed.
   * Draft → Plan Feed (E2a); same GuideScreen as Guide.
   */
  GuideExplore: {
    projectId: string;
    seed?: ProjectDetail;
    fromSession?: boolean;
  };
  Session: {
    projectId: string;
    /** After Manual apply — restore-state target for Undo banner. */
    undoVersion?: number | null;
    undoMessage?: string | null;
  };
  /** Guide trust surface — draft Explore + active roadmap (Slice C). */
  Guide: {
    projectId: string;
    seed?: ProjectDetail;
    /** Opened via Session ≡ — hide Start Session; expand full plan. */
    fromSession?: boolean;
  };
  /**
   * Manual editor for UI Block tools (Slice E2b) — Create plan card or
   * Active Session / Guide scope.
   */
  ManualEdit: {
    projectId: string;
    mode: 'create' | 'active';
    /** Create: plan card state_version to restore before edit. */
    stateVersion?: number | null;
    /** Create: plan card index to refresh after save. */
    planIndex?: number;
    /** Limit editor to this path-state action id (Create Block Edit + Active Session). */
    actionKey?: string | null;
  };
  Archive: undefined;
  Settings: undefined;
};

export type RootScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;
