import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import type { InstantAnswerResponse } from '@/api/types';

export type RootStackParamList = {
  Projects: undefined;
  Intent: undefined;
  InstantAnswer: { payload: InstantAnswerResponse };
  DraftStudio: { projectId: string };
  Accept: { projectId: string };
  ProjectHome: { projectId: string };
  Path: { projectId: string };
  History: undefined;
};

export type RootScreenProps<T extends keyof RootStackParamList> =
  NativeStackScreenProps<RootStackParamList, T>;
