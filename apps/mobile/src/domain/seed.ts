import { formatLocalDateTime, nextReminderFireAt, windowFromClosing } from './reminder';
import { COMPACT_TILE, type Cue, type Instance, type Subject, type Widget } from './types';

/**
 * Founder seed for the lid. IDs and texts come from packages/domain/fixtures.
 *
 * Law fixtures put push-ups and vegetables in `lifetime` so Python tests stay
 * honest. On the phone they must sit in Сегодня — otherwise the author never
 * sees the do-time cue at the moment of the set.
 *
 * Bike is not only here: a live warehouse already has push-ups/vegetables, so
 * `ensureBike` doseeds the bike without wiping those rows.
 */

export const BIKE_SUBJECT_ID = 'bike';
export const BIKE_CUE_ID = 'bike-gym-hours';
export const BIKE_INSTANCE_ID = 'bike-open';
export const BIKE_WIDGET_ID = 'bike-reminder';

export function buildBikeSeed(now: Date): {
  subject: Subject;
  cue: Cue;
  instance: Instance;
  widget: Widget;
} {
  const bikeWindow = windowFromClosing('22:00:00');
  const fireAt = nextReminderFireAt(bikeWindow, now);
  const fireIso = formatLocalDateTime(fireAt);

  return {
    subject: {
      id: BIKE_SUBJECT_ID,
      title: 'exercise bike',
      cadence: { count: 2, period: 'week' },
      window: bikeWindow,
      cue_ids: [BIKE_CUE_ID],
      target: null,
      instance_ids: [BIKE_INSTANCE_ID],
      status: 'active',
    },
    cue: {
      id: BIKE_CUE_ID,
      subject_id: BIKE_SUBJECT_ID,
      kind: 'correction',
      text: 'зал до 22',
      surface: 'timing',
      hits: { surfaced: 0, applied: 0 },
    },
    instance: {
      id: BIKE_INSTANCE_ID,
      subject_id: BIKE_SUBJECT_ID,
      when: fireIso,
      status: 'prepared',
    },
    widget: {
      id: BIKE_WIDGET_ID,
      type: 'reminder',
      title: 'exercise bike',
      payload: { fire_at: fireIso },
      status: 'ready',
      when: fireIso,
      section: 'today',
      subject_id: BIKE_SUBJECT_ID,
      instance_id: BIKE_INSTANCE_ID,
      tile_size: '4x1',
      version: 1,
    },
  };
}

export function buildSeed(nowIso: string): {
  subjects: Subject[];
  cues: Cue[];
  instances: Instance[];
  widgets: Widget[];
} {
  const subjects: Subject[] = [
    {
      id: 'push-ups',
      title: 'push-ups',
      cadence: { count: 3, period: 'week' },
      cue_ids: ['push-ups-brace'],
      target: { current: 28, goal: 30 },
      instance_ids: ['push-ups-open'],
      status: 'active',
    },
    {
      id: 'vegetables',
      title: 'vegetables',
      cadence: { count: 1, period: 'day' },
      cue_ids: [],
      target: null,
      instance_ids: ['vegetables-open'],
      status: 'active',
    },
  ];

  const cues: Cue[] = [
    {
      id: 'push-ups-brace',
      subject_id: 'push-ups',
      kind: 'correction',
      text: 'brace the core and the glutes',
      surface: 'do-time',
      hits: { surfaced: 0, applied: 0 },
    },
  ];

  const instances: Instance[] = [
    {
      id: 'push-ups-open',
      subject_id: 'push-ups',
      when: nowIso,
      status: 'prepared',
    },
    {
      id: 'vegetables-open',
      subject_id: 'vegetables',
      when: nowIso,
      status: 'prepared',
    },
  ];

  const widgets: Widget[] = [
    {
      id: 'push-ups-counter',
      type: 'counter',
      title: 'push-ups',
      payload: { count: 28, target: 30 },
      status: 'ready',
      when: null,
      section: 'today',
      subject_id: 'push-ups',
      instance_id: 'push-ups-open',
      tile_size: COMPACT_TILE,
      version: 1,
    },
    {
      id: 'vegetables-tick',
      type: 'tick',
      title: 'vegetables',
      payload: { done: false },
      status: 'ready',
      when: null,
      section: 'today',
      subject_id: 'vegetables',
      instance_id: 'vegetables-open',
      tile_size: COMPACT_TILE,
      version: 1,
    },
  ];

  return { subjects, cues, instances, widgets };
}

export function doTimeCueFor(cues: Cue[], subjectId: string): Cue | undefined {
  return cues.find((cue) => cue.subject_id === subjectId && cue.surface === 'do-time');
}
