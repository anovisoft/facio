import * as Notifications from 'expo-notifications';
import { useEffect, useRef } from 'react';

import { reminderDataOf } from '@/services/reminders';
import { useDesk } from '@/store/DeskContext';
import { getDb } from '@/store/database';
import { getMeta, setMeta } from '@/store/repository';
import { navigationRef } from './ref';

const LAST_OPENED_META = 'reminder_last_opened_id';

/**
 * Local reminder wiring: ask once when the bike appears, reschedule combat
 * from fire_at, open the lid on tap. Use for the bike is opened from the tile.
 */
export function ReminderBridge() {
  const desk = useDesk();
  const deskRef = useRef(desk);
  deskRef.current = desk;
  const synced = useRef(false);

  useEffect(() => {
    if (!desk.ready || synced.current) return;
    const hasReminder = desk.widgets.some((widget) => widget.type === 'reminder');
    if (!hasReminder) return;
    synced.current = true;
    desk.syncReminders().catch(() => undefined);
  }, [desk.ready, desk.syncReminders, desk.widgets]);

  useEffect(() => {
    const openLid = (notification: Notifications.Notification) => {
      if (!reminderDataOf(notification)) return;
      const id = notification.request.identifier;
      const database = getDb();
      if (getMeta(database, LAST_OPENED_META) === id) return;
      setMeta(database, LAST_OPENED_META, id);
      deskRef.current.noteReminderOpened(notification);
      if (navigationRef.isReady()) {
        navigationRef.navigate('Lid');
      }
    };

    const received = Notifications.addNotificationReceivedListener((notification) => {
      if (reminderDataOf(notification)) {
        deskRef.current.noteReminderFired(notification);
      }
    });
    const response = Notifications.addNotificationResponseReceivedListener((event) => {
      openLid(event.notification);
    });

    Notifications.getLastNotificationResponseAsync()
      .then((last) => {
        if (last) openLid(last.notification);
      })
      .catch(() => undefined);

    return () => {
      received.remove();
      response.remove();
    };
  }, []);

  return null;
}
