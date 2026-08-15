import { parseWhen } from './reminder';
import type { Cadence, DriftCard, DriftOffer, Instance, InstanceStatus, Subject } from './types';

/** Q27. Port of `facio_domain.drift`. Do not call Python. */
export const SILENCE_DAYS_WEEK = 8;
export const SILENCE_DAYS_DAY = 3;

const ACTIVITY = new Set<InstanceStatus>(['completed', 'in_progress']);

export function calendarDays(now: Date, then: Date): number {
  const start = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate());
  const end = Date.UTC(then.getFullYear(), then.getMonth(), then.getDate());
  return Math.round((start - end) / 86_400_000);
}

export function silenceThreshold(cadence: Cadence): number | null {
  if (cadence.period === 'none') return null;
  switch (cadence.period) {
    case 'week':
      return SILENCE_DAYS_WEEK;
    case 'day':
      return SILENCE_DAYS_DAY;
    default: {
      const exhaustive: never = cadence.period;
      return exhaustive;
    }
  }
}

export function lastActivityAt(subject: Subject, instances: Instance[]): Date | null {
  const own = instances.filter(
    (item) => item.subject_id === subject.id && ACTIVITY.has(item.status),
  );
  if (own.length === 0) return null;
  return own.reduce((latest, item) => {
    const when = parseWhen(item.when);
    return when > latest ? when : latest;
  }, parseWhen(own[0].when));
}

export function silenceDays(subject: Subject, instances: Instance[], now: Date): number | null {
  const last = lastActivityAt(subject, instances);
  if (!last) return null;
  return calendarDays(now, last);
}

export function isDrifting(subject: Subject, instances: Instance[], now: Date): boolean {
  if (subject.status === 'retired') return false;
  const threshold = silenceThreshold(subject.cadence);
  if (threshold == null) return false;
  const days = silenceDays(subject, instances, now);
  if (days == null) return false;
  return days >= threshold;
}

export function nextDriftOffer(asksMade: number, retireRefusals: number): DriftOffer {
  if (retireRefusals >= 2) return 'stop';
  if (asksMade <= 0) return 'move_to_today';
  if (asksMade === 1) return 'once_a_week';
  return 'retire';
}

function askedThisPeriod(subject: Subject, now: Date): boolean {
  if (!subject.last_asked) return false;
  const threshold = silenceThreshold(subject.cadence);
  if (threshold == null) return false;
  return calendarDays(now, parseWhen(subject.last_asked)) < threshold;
}

/**
 * At most one drift card. Oldest silence wins.
 * Answered this period or `stop` → no card (ignore still shows).
 */
export function driftCard(
  subjects: Subject[],
  instances: Instance[],
  now: Date,
): DriftCard | null {
  const drifting: { days: number; id: string; offer: DriftOffer }[] = [];
  for (const subject of subjects) {
    if (!isDrifting(subject, instances, now)) continue;
    if (askedThisPeriod(subject, now)) continue;
    const days = silenceDays(subject, instances, now);
    if (days == null) continue;
    const offer = nextDriftOffer(subject.asks_made ?? 0, subject.retire_refusals ?? 0);
    if (offer === 'stop') continue;
    drifting.push({ days, id: subject.id, offer });
  }
  if (drifting.length === 0) return null;
  const oldest = drifting.reduce((best, row) => {
    if (row.days > best.days) return row;
    if (row.days === best.days && row.id > best.id) return row;
    return best;
  });
  return {
    subject_id: oldest.id,
    silent_days: oldest.days,
    offer: oldest.offer,
  };
}
