import type { Window } from './types';

/** Law: `CLOSING_LEAD` — gym shuts at 22 → fire at 19. Port, do not call Python. */
export const CLOSING_LEAD_HOURS = 3;

export function parseClock(value: string): { hours: number; minutes: number; seconds: number } {
  const [hours, minutes, seconds] = value.split(':').map((part) => Number.parseInt(part, 10));
  return {
    hours: Number.isFinite(hours) ? hours : 0,
    minutes: Number.isFinite(minutes) ? minutes : 0,
    seconds: Number.isFinite(seconds) ? seconds : 0,
  };
}

export function formatClock(hours: number, minutes: number, seconds = 0): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

export function parseLocalDateTime(iso: string): Date {
  const [datePart, timePart = '00:00:00'] = iso.split('T');
  const [year, month, day] = datePart.split('-').map((part) => Number.parseInt(part, 10));
  const clock = parseClock(timePart);
  return new Date(year, (month ?? 1) - 1, day ?? 1, clock.hours, clock.minutes, clock.seconds, 0);
}

export function formatLocalDateTime(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${formatClock(
    date.getHours(),
    date.getMinutes(),
    date.getSeconds(),
  )}`;
}

/** Law `window_from_closing`: latest_by = closes_at minus 3 hours. */
export function windowFromClosing(closesAt: string): Window {
  const clock = parseClock(closesAt);
  const base = new Date(2000, 0, 1, clock.hours, clock.minutes, clock.seconds);
  const latest = new Date(base.getTime() - CLOSING_LEAD_HOURS * 60 * 60 * 1000);
  return {
    latest_by: formatClock(latest.getHours(), latest.getMinutes(), latest.getSeconds()),
    closes_at: closesAt,
  };
}

/** Law `reminder_fire_at`: the window sets the hour. */
export function reminderFireAt(window: Window, onDate: Date): Date {
  const clock = parseClock(window.latest_by);
  return new Date(
    onDate.getFullYear(),
    onDate.getMonth(),
    onDate.getDate(),
    clock.hours,
    clock.minutes,
    clock.seconds,
    0,
  );
}

/** Next combat slot: today at latest_by if still ahead, otherwise tomorrow. */
export function nextReminderFireAt(window: Window, now = new Date()): Date {
  const today = reminderFireAt(window, now);
  if (today.getTime() > now.getTime()) return today;
  const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
  return reminderFireAt(window, tomorrow);
}

export function formatFireClock(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = parseLocalDateTime(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', hour12: false });
}

/** Clock the finger owns after a window edit; seed still comes from closing−3h. */
export function clockPartsFromWindow(
  window: Window | null | undefined,
  fireAt?: string | null,
): { hours: number; minutes: number } {
  if (window?.latest_by) {
    const clock = parseClock(window.latest_by);
    return { hours: clock.hours, minutes: clock.minutes };
  }
  if (fireAt) {
    const date = parseLocalDateTime(fireAt);
    if (!Number.isNaN(date.getTime())) {
      return { hours: date.getHours(), minutes: date.getMinutes() };
    }
  }
  return { hours: 19, minutes: 0 };
}
