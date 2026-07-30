import { apiRequest } from '@/api/client';
import type { ListStatusFilter, ProjectSummary } from '@/api/types';

export function listProjects(
  status: ListStatusFilter = 'open',
  signal?: AbortSignal,
): Promise<ProjectSummary[]> {
  return apiRequest('/projects', { query: { status }, signal });
}
