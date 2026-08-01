import { apiRequest } from '@/api/client';
import type {
  CreateIntentResponse,
  FirstStepWhen,
  ListStatusFilter,
  ProjectDetail,
  ProjectSummary,
  RefineAnswerItem,
  RepairIntent,
  StateVersionSummary,
} from '@/api/types';
import { getLocalDate } from '@/services/localDate';

export function listProjects(
  status: ListStatusFilter = 'open',
  signal?: AbortSignal,
): Promise<ProjectSummary[]> {
  return apiRequest('/projects', {
    query: { status, local_date: getLocalDate() },
    signal,
  });
}

export function createProject(
  intent: string,
  signal?: AbortSignal,
): Promise<CreateIntentResponse> {
  return apiRequest('/projects', {
    method: 'POST',
    body: { intent },
    signal,
  });
}

export function getProject(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}`, {
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function refineProject(
  projectId: string,
  payload: {
    answers?: RefineAnswerItem[];
    comment?: string | null;
  },
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  const body: {
    answers?: RefineAnswerItem[];
    comment?: string;
  } = {};
  if (payload.answers && payload.answers.length > 0) {
    body.answers = payload.answers;
  }
  const comment = payload.comment?.trim();
  if (comment) {
    body.comment = comment;
  }
  return apiRequest(`/projects/${projectId}/refine`, {
    method: 'POST',
    body,
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function listStateVersions(
  projectId: string,
  signal?: AbortSignal,
): Promise<StateVersionSummary[]> {
  return apiRequest(`/projects/${projectId}/state-versions`, { signal });
}

export function restoreState(
  projectId: string,
  version: number,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/restore-state`, {
    method: 'POST',
    body: { version },
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function commitProject(
  projectId: string,
  firstStepWhen: FirstStepWhen = 'today',
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/commit`, {
    method: 'POST',
    body: { first_step_when: firstStepWhen },
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function abandonProject(
  projectId: string,
  reason?: string | null,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/abandon`, {
    method: 'POST',
    body: reason ? { reason } : {},
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function repairProject(
  projectId: string,
  payload: { intent?: RepairIntent; reason?: string },
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  const body: { intent?: RepairIntent; reason?: string } = {};
  if (payload.intent) body.intent = payload.intent;
  const reason = payload.reason?.trim();
  if (reason) body.reason = reason;
  return apiRequest(`/projects/${projectId}/repair`, {
    method: 'POST',
    body,
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function rematerializePlugins(
  projectId: string,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/materialize-plugins`, {
    method: 'POST',
    query: { local_date: getLocalDate() },
    signal,
  });
}
