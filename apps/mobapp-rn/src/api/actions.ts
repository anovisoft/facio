import { apiRequest } from '@/api/client';
import type { ActionResponse, ChecklistItemResponse } from '@/api/types';

export function completeAction(
  actionId: string,
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/complete`, {
    method: 'POST',
    signal,
  });
}

export function skipAction(
  actionId: string,
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/skip`, {
    method: 'POST',
    signal,
  });
}

export function toggleChecklistItem(
  itemId: string,
  done?: boolean | null,
  signal?: AbortSignal,
): Promise<ChecklistItemResponse> {
  return apiRequest(`/checklist-items/${itemId}/toggle`, {
    method: 'POST',
    body: done == null ? {} : { done },
    signal,
  });
}
