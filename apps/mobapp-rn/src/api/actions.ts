import { apiRequest } from '@/api/client';
import type { ActionResponse, ChecklistItemResponse } from '@/api/types';
import { getLocalDate } from '@/services/localDate';

export function completeAction(
  actionId: string,
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/complete`, {
    method: 'POST',
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function skipAction(
  actionId: string,
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/skip`, {
    method: 'POST',
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function uncompleteAction(
  actionId: string,
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(`/actions/${actionId}/uncomplete`, {
    method: 'POST',
    query: { local_date: getLocalDate() },
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
    query: { local_date: getLocalDate() },
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
    query: { local_date: getLocalDate() },
    signal,
  });
}

export function updateStepperBeatCounter(
  actionId: string,
  beatId: string,
  body: { current?: number; delta?: number },
  signal?: AbortSignal,
): Promise<ActionResponse> {
  return apiRequest(
    `/actions/${actionId}/stepper/beats/${beatId}/counter`,
    {
      method: 'POST',
      body,
      query: { local_date: getLocalDate() },
      signal,
    },
  );
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
    query: { local_date: getLocalDate() },
    signal,
  });
}
