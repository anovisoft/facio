import { openDatabaseSync, type SQLiteDatabase } from 'expo-sqlite';

const DB_NAME = 'facio.db';

let db: SQLiteDatabase | null = null;

export function getDb(): SQLiteDatabase {
  if (!db) {
    db = openDatabaseSync(DB_NAME);
    migrate(db);
  }
  return db;
}

function migrate(database: SQLiteDatabase): void {
  database.execSync(`
    PRAGMA journal_mode = WAL;
    CREATE TABLE IF NOT EXISTS subjects (
      id TEXT PRIMARY KEY NOT NULL,
      json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS cues (
      id TEXT PRIMARY KEY NOT NULL,
      subject_id TEXT NOT NULL,
      json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS instances (
      id TEXT PRIMARY KEY NOT NULL,
      subject_id TEXT NOT NULL,
      json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS widgets (
      id TEXT PRIMARY KEY NOT NULL,
      subject_id TEXT NOT NULL,
      instance_id TEXT NOT NULL,
      json TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY NOT NULL,
      type TEXT NOT NULL,
      at TEXT NOT NULL,
      subject_id TEXT,
      widget_id TEXT,
      instance_id TEXT,
      cue_id TEXT,
      payload TEXT
    );
    CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY NOT NULL,
      value TEXT NOT NULL
    );
  `);
}

export function storeIsEmpty(database: SQLiteDatabase): boolean {
  const row = database.getFirstSync<{ n: number }>('SELECT COUNT(*) AS n FROM subjects');
  return (row?.n ?? 0) === 0;
}
