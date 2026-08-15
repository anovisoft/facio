import * as Crypto from 'expo-crypto';
import type { SQLiteDatabase } from 'expo-sqlite';

import { addCalendarDays, formatLocalDateTime, parseWhen, sameCalendarDay } from '@/domain/reminder';
import {
  BIKE_SUBJECT_ID,
  buildBikeFoundingCompleted,
  buildBikeSeed,
  buildSeed,
} from '@/domain/seed';
import type {
  Cue,
  DeskSnapshot,
  Instance,
  JournalEvent,
  JournalEventType,
  Subject,
  Widget,
} from '@/domain/types';
import { storeIsEmpty } from './database';

type EntityRow = { id: string; json: string };

function parseAll<T>(rows: EntityRow[]): T[] {
  return rows.map((row) => JSON.parse(row.json) as T);
}

export function loadSnapshot(database: SQLiteDatabase): DeskSnapshot {
  return {
    subjects: parseAll<Subject>(database.getAllSync<EntityRow>('SELECT id, json FROM subjects')),
    cues: parseAll<Cue>(database.getAllSync<EntityRow>('SELECT id, json FROM cues')),
    instances: parseAll<Instance>(database.getAllSync<EntityRow>('SELECT id, json FROM instances')),
    widgets: parseAll<Widget>(database.getAllSync<EntityRow>('SELECT id, json FROM widgets')),
  };
}

export function saveSubject(database: SQLiteDatabase, subject: Subject): void {
  database.runSync('INSERT OR REPLACE INTO subjects (id, json) VALUES (?, ?)', [
    subject.id,
    JSON.stringify(subject),
  ]);
}

export function saveCue(database: SQLiteDatabase, cue: Cue): void {
  database.runSync('INSERT OR REPLACE INTO cues (id, subject_id, json) VALUES (?, ?, ?)', [
    cue.id,
    cue.subject_id,
    JSON.stringify(cue),
  ]);
}

export function saveInstance(database: SQLiteDatabase, instance: Instance): void {
  database.runSync('INSERT OR REPLACE INTO instances (id, subject_id, json) VALUES (?, ?, ?)', [
    instance.id,
    instance.subject_id,
    JSON.stringify(instance),
  ]);
}

export function saveWidget(database: SQLiteDatabase, widget: Widget): void {
  database.runSync(
    'INSERT OR REPLACE INTO widgets (id, subject_id, instance_id, json) VALUES (?, ?, ?, ?)',
    [widget.id, widget.subject_id, widget.instance_id, JSON.stringify(widget)],
  );
}

export function getMeta(database: SQLiteDatabase, key: string): string | null {
  const row = database.getFirstSync<{ value: string }>(
    'SELECT value FROM meta WHERE key = ?',
    [key],
  );
  return row?.value ?? null;
}

export function setMeta(database: SQLiteDatabase, key: string, value: string): void {
  database.runSync('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', [key, value]);
}

export function appendEvent(
  database: SQLiteDatabase,
  type: JournalEventType,
  fields: Omit<JournalEvent, 'id' | 'type' | 'at'> & { at?: string },
): JournalEvent {
  const event: JournalEvent = {
    id: Crypto.randomUUID(),
    type,
    at: fields.at ?? new Date().toISOString(),
    subject_id: fields.subject_id ?? null,
    widget_id: fields.widget_id ?? null,
    instance_id: fields.instance_id ?? null,
    cue_id: fields.cue_id ?? null,
    payload: fields.payload ?? null,
  };
  database.runSync(
    `INSERT INTO events (id, type, at, subject_id, widget_id, instance_id, cue_id, payload)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      event.id,
      event.type,
      event.at,
      event.subject_id ?? null,
      event.widget_id ?? null,
      event.instance_id ?? null,
      event.cue_id ?? null,
      event.payload ? JSON.stringify(event.payload) : null,
    ],
  );
  return event;
}

export function seedIfEmpty(database: SQLiteDatabase): DeskSnapshot {
  if (!storeIsEmpty(database)) {
    return loadSnapshot(database);
  }

  const nowIso = new Date().toISOString();
  const seed = buildSeed(nowIso);

  database.withTransactionSync(() => {
    for (const subject of seed.subjects) saveSubject(database, subject);
    for (const cue of seed.cues) {
      saveCue(database, cue);
      appendEvent(database, 'cue_written', {
        subject_id: cue.subject_id,
        cue_id: cue.id,
        payload: { text: cue.text, surface: cue.surface },
      });
    }
    for (const instance of seed.instances) saveInstance(database, instance);
    for (const widget of seed.widgets) saveWidget(database, widget);
    database.runSync('INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)', ['seeded_at', nowIso]);
  });

  return loadSnapshot(database);
}

/**
 * Doseed the founding bike on a live warehouse. Does not rewrite push-ups
 * or vegetables. `seedIfEmpty` never runs again once the author has lived
 * step 1 — this is the path that matters.
 */
export const MORNING_CLOSED_META_KEY = 'morning_card_closed_on';

export function ensureBike(database: SQLiteDatabase, now = new Date()): DeskSnapshot {
  const snapshot = loadSnapshot(database);
  if (snapshot.subjects.some((subject) => subject.id === BIKE_SUBJECT_ID)) {
    return snapshot;
  }

  const seed = buildBikeSeed(now);
  database.withTransactionSync(() => {
    saveSubject(database, seed.subject);
    saveCue(database, seed.cue);
    appendEvent(database, 'cue_written', {
      subject_id: seed.cue.subject_id,
      cue_id: seed.cue.id,
      payload: { text: seed.cue.text, surface: seed.cue.surface },
    });
    saveInstance(database, seed.instance);
    saveWidget(database, seed.widget);
  });

  return loadSnapshot(database);
}

/**
 * Never-started is not drift. On a live warehouse the bike often has only
 * a prepared reminder — doseed one completed instance 21 days ago.
 */
export function ensureBikeFoundingSilence(
  database: SQLiteDatabase,
  now = new Date(),
): DeskSnapshot {
  const snapshot = loadSnapshot(database);
  const bike = snapshot.subjects.find((subject) => subject.id === BIKE_SUBJECT_ID);
  if (!bike) return snapshot;

  const hasActivity = snapshot.instances.some(
    (item) =>
      item.subject_id === BIKE_SUBJECT_ID &&
      (item.status === 'completed' || item.status === 'in_progress'),
  );
  if (hasActivity) return snapshot;

  const founding = buildBikeFoundingCompleted(now);
  const nextSubject: Subject = {
    ...bike,
    instance_ids: bike.instance_ids.includes(founding.id)
      ? bike.instance_ids
      : [...bike.instance_ids, founding.id],
  };
  database.withTransactionSync(() => {
    saveInstance(database, founding);
    saveSubject(database, nextSubject);
  });
  return loadSnapshot(database);
}

export function setLastCompletedWhen(
  database: SQLiteDatabase,
  subjectId: string,
  when: Date,
): DeskSnapshot {
  const snapshot = loadSnapshot(database);
  const own = snapshot.instances.filter(
    (item) =>
      item.subject_id === subjectId &&
      (item.status === 'completed' || item.status === 'in_progress'),
  );
  const whenIso = formatLocalDateTime(when);
  let target = own.reduce<Instance | null>((latest, item) => {
    if (!latest) return item;
    return parseWhen(item.when) > parseWhen(latest.when) ? item : latest;
  }, null);
  const subject = snapshot.subjects.find((item) => item.id === subjectId);

  database.withTransactionSync(() => {
    if (!target) {
      target =
        subjectId === BIKE_SUBJECT_ID
          ? { ...buildBikeFoundingCompleted(when), when: whenIso }
          : {
              id: `${subjectId}-silence`,
              subject_id: subjectId,
              when: whenIso,
              status: 'completed',
            };
      saveInstance(database, target);
    } else {
      saveInstance(database, { ...target, when: whenIso, status: 'completed' });
    }
    if (subject) {
      const ids = subject.instance_ids.includes(target.id)
        ? subject.instance_ids
        : [...subject.instance_ids, target.id];
      saveSubject(database, { ...subject, instance_ids: ids, last_asked: null });
    }
  });
  return loadSnapshot(database);
}

/** Debug: un-retire the bike and plant silence so the drift card returns. */
export function restoreBikeDrift(
  database: SQLiteDatabase,
  days: 8 | 21,
  now = new Date(),
): DeskSnapshot {
  const snapshot = setLastCompletedWhen(database, BIKE_SUBJECT_ID, addCalendarDays(now, -days));
  const bike = snapshot.subjects.find((subject) => subject.id === BIKE_SUBJECT_ID);
  if (!bike) return snapshot;
  const needsCadence = bike.status === 'retired' || bike.cadence.period === 'none';
  const next: Subject = {
    ...bike,
    status: 'active',
    cadence: needsCadence ? { count: 2, period: 'week' } : bike.cadence,
    last_asked: null,
    asks_made: 0,
    retire_refusals: 0,
  };
  saveSubject(database, next);
  return loadSnapshot(database);
}

/**
 * Done today belongs on Today. Lifetime leftovers with today's `when`
 * come back; other days stay in the warehouse and leave the lid.
 */
export function restoreTodayDone(database: SQLiteDatabase, now = new Date()): DeskSnapshot {
  const snapshot = loadSnapshot(database);
  const rows = database.getAllSync<{ widget_id: string; at: string }>(
    `SELECT widget_id, at FROM events
     WHERE type = 'instance_completed' AND widget_id IS NOT NULL
     ORDER BY at ASC`,
  );
  const completedAt = new Map<string, string>();
  for (const row of rows) {
    completedAt.set(row.widget_id, row.at);
  }

  database.withTransactionSync(() => {
    for (const widget of snapshot.widgets) {
      if (widget.status !== 'done') continue;
      const instance = snapshot.instances.find((item) => item.id === widget.instance_id);
      const rawWhen = widget.when ?? instance?.when ?? completedAt.get(widget.id) ?? null;
      if (!rawWhen) continue;
      const whenDate = parseWhen(rawWhen);
      if (Number.isNaN(whenDate.getTime())) continue;
      const whenLocal = formatLocalDateTime(whenDate);
      const nextSection = sameCalendarDay(whenDate, now) ? 'today' : widget.section;
      if (widget.when === whenLocal && widget.section === nextSection) continue;
      saveWidget(database, { ...widget, when: whenLocal, section: nextSection });
      if (instance && instance.status === 'completed' && instance.when !== whenLocal) {
        saveInstance(database, { ...instance, when: whenLocal });
      }
    }
  });
  return loadSnapshot(database);
}

/**
 * Opening Use used to mark the counter running. A warehouse that only
 * looked still has `running` / `in_progress` and a jumped grid. Revert
 * those rows unless a real +/- was journaled.
 */
export function revertLookOnlyStarts(database: SQLiteDatabase): DeskSnapshot {
  const snapshot = loadSnapshot(database);
  const ticked = new Set(
    database
      .getAllSync<{ widget_id: string }>(
        `SELECT DISTINCT widget_id FROM events
         WHERE type = 'counter_ticked' AND widget_id IS NOT NULL`,
      )
      .map((row) => row.widget_id),
  );

  database.withTransactionSync(() => {
    for (const widget of snapshot.widgets) {
      if (widget.type !== 'counter' || widget.status !== 'running') continue;
      if (ticked.has(widget.id)) continue;
      const instance = snapshot.instances.find((item) => item.id === widget.instance_id);
      if (!instance || instance.status === 'completed') continue;
      saveWidget(database, { ...widget, status: 'ready' });
      if (instance.status === 'in_progress') {
        saveInstance(database, { ...instance, status: 'prepared' });
      }
    }
  });

  return loadSnapshot(database);
}
