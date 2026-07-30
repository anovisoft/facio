import * as Haptics from 'expo-haptics';
import * as Notifications from 'expo-notifications';
import { Platform, Vibration } from 'react-native';

import type { TimerSignal } from '@/api/types';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowBanner: true,
    shouldShowList: true,
    shouldPlaySound: true,
    shouldSetBadge: false,
  }),
});

let permissionAsked = false;

export async function ensureNotificationPermission(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  const current = await Notifications.getPermissionsAsync();
  if (
    current.granted ||
    current.ios?.status === Notifications.IosAuthorizationStatus.PROVISIONAL
  ) {
    return true;
  }
  if (permissionAsked && !current.canAskAgain) return false;
  permissionAsked = true;
  const next = await Notifications.requestPermissionsAsync();
  return Boolean(next.granted);
}

export async function signalTimerComplete(
  title: string,
  signal: TimerSignal,
): Promise<void> {
  if (signal === 'alert') {
    Vibration.vibrate([0, 400, 120, 400, 120, 600]);
    try {
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    } catch {
      // Simulator / unsupported
    }
  } else {
    Vibration.vibrate(180);
    try {
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch {
      // Simulator / unsupported
    }
  }

  const allowed = await ensureNotificationPermission();
  if (!allowed) return;
  try {
    await Notifications.scheduleNotificationAsync({
      content: {
        title: signal === 'alert' ? `⏱ ${title}` : title,
        body:
          signal === 'alert'
            ? 'Time is up — critical cooking step'
            : 'Timer finished',
        sound: signal === 'alert',
        priority:
          signal === 'alert'
            ? Notifications.AndroidNotificationPriority.MAX
            : Notifications.AndroidNotificationPriority.DEFAULT,
      },
      trigger: null,
    });
  } catch {
    // Permission / platform edge cases
  }
}

export async function scheduleTimerNotification(
  timerId: string,
  title: string,
  signal: TimerSignal,
  endsAtMs: number,
): Promise<string | null> {
  const allowed = await ensureNotificationPermission();
  if (!allowed) return null;
  const seconds = Math.max(1, Math.round((endsAtMs - Date.now()) / 1000));
  try {
    return await Notifications.scheduleNotificationAsync({
      content: {
        title: signal === 'alert' ? `⏱ ${title}` : title,
        body:
          signal === 'alert'
            ? 'Time is up — critical cooking step'
            : 'Timer finished',
        sound: signal === 'alert',
        data: { timerId, signal },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.TIME_INTERVAL,
        seconds,
        repeats: false,
      },
    });
  } catch {
    return null;
  }
}

export async function cancelScheduledNotification(
  notificationId: string | null | undefined,
): Promise<void> {
  if (!notificationId) return;
  try {
    await Notifications.cancelScheduledNotificationAsync(notificationId);
  } catch {
    // already fired / cancelled
  }
}
