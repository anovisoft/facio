/**
 * Device local calendar date (YYYY-MM-DD), sent to the backend so the
 * physical-day unlock gate (docs/next/04 §4) uses the user's timezone
 * instead of the server's UTC clock.
 */
export function getLocalDate(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export type UnlockTiming = 'today' | 'tomorrow' | 'later';

/** Classify a `next_unlock_date` (YYYY-MM-DD) relative to device local today. */
export function classifyUnlockDate(
  unlockDateIso: string,
  now: Date = new Date(),
): UnlockTiming {
  if (unlockDateIso === getLocalDate(now)) return 'today';
  const tomorrow = new Date(now);
  tomorrow.setDate(tomorrow.getDate() + 1);
  if (unlockDateIso === getLocalDate(tomorrow)) return 'tomorrow';
  return 'later';
}
