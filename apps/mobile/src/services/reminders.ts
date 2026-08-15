import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';

import { formatFireClock, parseLocalDateTime } from '@/domain/reminder';
import type { Widget } from '@/domain/types';

export type ReminderKind = 'combat' | 'dogfood';

export type ReminderNotificationData = {
  widgetId: string;
  subjectId: string;
  kind: ReminderKind;
};

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

const PERMISSION_META_KEY = 'reminder_permission_asked';
let permissionAskedThisSession = false;

function isReminderData(value: unknown): value is ReminderNotificationData {
  if (!value || typeof value !== 'object') return false;
  const data = value as ReminderNotificationData;
  return typeof data.widgetId === 'string' && (data.kind === 'combat' || data.kind === 'dogfood');
}

export function reminderDataOf(
  notification: Notifications.Notification,
): ReminderNotificationData | null {
  return isReminderData(notification.request.content.data)
    ? notification.request.content.data
    : null;
}

export async function ensureNotificationPermission(options?: {
  force?: boolean;
  alreadyAsked?: boolean;
}): Promise<boolean> {
  if (Platform.OS === 'web') return false;

  const current = await Notifications.getPermissionsAsync();
  if (
    current.granted ||
    current.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL
  ) {
    return true;
  }

  const askedBefore = options?.alreadyAsked || permissionAskedThisSession;
  if (!options?.force && askedBefore && !current.canAskAgain) {
    return false;
  }
  if (!options?.force && askedBefore) {
    return false;
  }

  permissionAskedThisSession = true;
  await ensureAndroidChannel();

  const next = await Notifications.requestPermissionsAsync();
  return Boolean(next.granted);
}

async function ensureAndroidChannel(): Promise<void> {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync('reminders', {
    name: 'Reminders',
    importance: Notifications.AndroidImportance.HIGH,
  });
}

export { PERMISSION_META_KEY };

export async function cancelWidgetNotifications(
  widgetId: string,
  kinds?: ReminderKind[],
): Promise<void> {
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  for (const item of scheduled) {
    const raw = item.content.data;
    if (!isReminderData(raw) || raw.widgetId !== widgetId) continue;
    if (kinds && !kinds.includes(raw.kind)) continue;
    try {
      await Notifications.cancelScheduledNotificationAsync(item.identifier);
    } catch {
      // already fired / cancelled
    }
  }
}

function combatBody(fireAtIso: string): string {
  const clock = formatFireClock(fireAtIso);
  return clock ? `окно до ${clock}` : 'окно велосипеда';
}

export async function scheduleCombatReminder(widget: Widget, fireAt: Date): Promise<string | null> {
  const fireIso = widget.payload.fire_at;
  if (!fireIso || fireAt.getTime() <= Date.now()) return null;
  try {
    await ensureAndroidChannel();
    return await Notifications.scheduleNotificationAsync({
      content: {
        title: widget.title,
        body: combatBody(fireIso),
        sound: true,
        ...(Platform.OS === 'android' ? { channelId: 'reminders' } : {}),
        data: {
          widgetId: widget.id,
          subjectId: widget.subject_id,
          kind: 'combat',
        } satisfies ReminderNotificationData,
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: fireAt,
      },
    });
  } catch {
    return null;
  }
}

/**
 * Dogfood only: one-shot local notify in ~60s.
 * Does not cancel or replace the combat fire_at slot. After the check,
 * the 19:00 (or next) combat remains scheduled.
 */
export async function scheduleDogfoodReminder(widget: Widget, seconds = 60): Promise<string | null> {
  try {
    await ensureAndroidChannel();
    return await Notifications.scheduleNotificationAsync({
      content: {
        title: widget.title,
        body: 'напомнить через минуту',
        sound: true,
        ...(Platform.OS === 'android' ? { channelId: 'reminders' } : {}),
        data: {
          widgetId: widget.id,
          subjectId: widget.subject_id,
          kind: 'dogfood',
        } satisfies ReminderNotificationData,
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
        seconds: Math.max(1, seconds),
        repeats: false,
      },
    });
  } catch {
    return null;
  }
}

export function fireAtFromPayload(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const date = parseLocalDateTime(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}
