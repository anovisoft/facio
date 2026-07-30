import { apiRequest } from '@/api/client';
import type {
  CreateIntentResponse,
  FirstStepWhen,
  ListStatusFilter,
  ProjectDetail,
  ProjectSummary,
  StateVersionSummary,
} from '@/api/types';

export function listProjects(
  status: ListStatusFilter = 'open',
  signal?: AbortSignal,
): Promise<ProjectSummary[]> {
  return apiRequest('/projects', { query: { status }, signal });
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
  return apiRequest(`/projects/${projectId}`, { signal });
}

export function listActions(projectId: string, signal?: AbortSignal) {
  return apiRequest(`/projects/${projectId}/actions`, { signal });
}

export function listStateVersions(
  projectId: string,
  signal?: AbortSignal,
): Promise<StateVersionSummary[]> {
  return apiRequest(`/projects/${projectId}/state-versions`, { signal });
}

export function refineProject(
  projectId: string,
  answer: string,
  questionId?: string | null,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/refine`, {
    method: 'POST',
    body: { answer, question_id: questionId ?? null },
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
    body: { reason: reason ?? null },
    signal,
  });
}

export function restoreState(
  projectId: string,
  version: number,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/restore-state`, {
    method: 'POST',
    body: { version },
    signal,
  });
}

export function repairProject(
  projectId: string,
  reason: string,
  signal?: AbortSignal,
): Promise<ProjectDetail> {
  return apiRequest(`/projects/${projectId}/repair`, {
    method: 'POST',
    body: { reason },
    signal,
  });
}
