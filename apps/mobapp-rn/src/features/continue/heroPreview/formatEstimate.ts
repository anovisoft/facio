/** Format Session estimate for Hero Preview footer (read-only). */

export function formatApproxMin(
  estimateMin: number | null | undefined,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string | null {
  if (estimateMin == null || estimateMin < 0) return null;
  return t('continue.approxMin', { count: estimateMin });
}

export function formatClock(totalSec: number): string {
  const sec = Math.max(0, Math.ceil(totalSec));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}
