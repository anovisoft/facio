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
   * Same GuideScreen chrome (Cover + roadmap + Start Guide).
   */
  GuideExplore: {
    projectId: string;
    seed?: ProjectDetail;
    fromSession?: boolean;
  };
  Session: { projectId: string };
  /** Guide trust surface — draft Explore + active roadmap (Slice C). */
  Guide: {
    projectId: string;
    seed?: ProjectDetail;
    /** Opened via Session ≡ — hide Start Session; expand full plan. */
    fromSession?: boolean;
  };
  Archive: undefined;
  Settings: undefined;
};

export type RootScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;
