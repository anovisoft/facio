import * as Crypto from 'expo-crypto';
import type { SQLiteDatabase } from 'expo-sqlite';

import { BIKE_SUBJECT_ID, buildBikeSeed, buildSeed } from '@/domain/seed';
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
