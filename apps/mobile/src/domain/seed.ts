import { COMPACT_TILE, type Cue, type Instance, type Subject, type Widget } from './types';

/**
 * Founder seed for the lid. IDs and texts come from packages/domain/fixtures.
 *
 * Law fixtures put push-ups and vegetables in `lifetime` so Python tests stay
 * honest. On the phone they must sit in Сегодня — otherwise the author never
 * sees the do-time cue at the moment of the set.
 *
 * Bike is step 2. Not seeded.
 */
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
