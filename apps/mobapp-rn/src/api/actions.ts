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

export function updateCounter(
  actionId: string,
  body: { current?: number; delta?: number },
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/counter`, {
    method: 'POST',
    body,
    signal,
  });
}

export function completeTimer(
  actionId: string,
  timerId: string,
  completed = true,
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/timers/${timerId}/complete`, {
    method: 'POST',
    body: { completed },
    signal,
  });
}
