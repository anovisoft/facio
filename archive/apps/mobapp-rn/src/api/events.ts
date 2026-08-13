import { apiRequest } from '@/api/client';
import type { ClientBeaconType, EventResponse } from '@/api/types';

export function postEvent(
  type: ClientBeaconType,
  opts?: {
    projectId?: string | null;
    payload?: Record<string, unknown>;
  },
): Promise<EventResponse> {
  return apiRequest('/events', {
    method: 'POST',
    body: {
      type,
      project_id: opts?.projectId ?? null,
      payload: opts?.payload ?? {},
    },
  });
}
