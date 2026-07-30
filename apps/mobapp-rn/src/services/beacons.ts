/**
 * UI beacons only — never duplicate server mutation event types.
 * @see docs/mvp/05-tech-slice.md
 */

import { postEvent } from '@/api/events';

async function fire(
  type: Parameters<typeof postEvent>[0],
  opts?: Parameters<typeof postEvent>[1],
): Promise<void> {
  try {
    await postEvent(type, opts);
  } catch (error) {
    if (__DEV__) {
      console.warn(`[beacon] ${type} failed`, error);
    }
  }
}

export function trackAppOpened(projectId?: string | null): void {
  void fire('app_opened', { projectId });
}

export function trackAcceptViewed(projectId: string): void {
  void fire('accept_viewed', { projectId });
}

export function trackActionShown(projectId: string, actionId: string): void {
  void fire('action_shown', {
    projectId,
    payload: { action_id: actionId },
  });
}

export function trackPathOpened(projectId: string): void {
  void fire('path_opened', { projectId });
}

export function trackProjectSwitched(projectId: string): void {
  void fire('project_switched', { projectId });
}
