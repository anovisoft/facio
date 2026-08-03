import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { InstantAnswerResponse, ProjectDetail } from '@/api/types';

/**
 * Facio 0.1 IA routes (Slice A).
 * Prototype aliases: Continue←Projects, Session←ProjectHome,
 * Guide←Path, GuideExplore←DraftStudio, Create←Intent, Archive←History.
 * InstantAnswer stays typed/registered but is off the Create happy path (D5).
 */
export type RootStackParamList = {
  Continue: undefined;
  Create: undefined;
  /** Dead route — not linked from Create (D5). Screen kept for now. */
  InstantAnswer: { payload: InstantAnswerResponse };
  /** Pre-commitment Guide Explore (prototype DraftStudio). */
  GuideExplore: { projectId: string; seed?: ProjectDetail };
  Session: { projectId: string };
  /** Post-commitment Guide roadmap (prototype Path). */
  Guide: { projectId: string };
  Archive: undefined;
  Settings: undefined;
};

export type RootScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;
