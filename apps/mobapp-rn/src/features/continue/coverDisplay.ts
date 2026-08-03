/**
 * Display fallbacks for Guide Cover when API fields are null (pre-Slice B rows).
 * Persisted covers come from the API; this only fills the glance layer.
 */

import type { ProjectSummary } from '@/api/types';

const DOMAIN_EMOJI: Record<string, string> = {
  cooking: '🍝',
  fitness: '🏋️',
  learning: '📚',
  home: '🏠',
  errands: '🛒',
  work: '💼',
  health: '💚',
  finance: '💰',
  social: '👋',
  other: '✨',
};

function titleMark(title: string | null | undefined): string {
  const raw = (title || '').trim();
  if (!raw) return '✨';
  for (const ch of raw) {
    if (/[0-9A-Za-zА-Яа-яЁё]/.test(ch)) return ch.toUpperCase();
  }
  return raw[0] ?? '✨';
}

export type GuideCover = {
  emoji: string;
  difficulty: string | null;
  durationSummary: string | null;
};

export function resolveGuideCover(guide: ProjectSummary): GuideCover {
  const title = guide.title || guide.outcome || guide.raw_intent;
  const emoji =
    guide.cover_emoji?.trim() ||
    (guide.domain ? DOMAIN_EMOJI[guide.domain] : null) ||
    titleMark(title);

  const difficulty = guide.cover_difficulty?.trim() || null;
  const durationSummary =
    guide.cover_duration_summary?.trim() ||
    guide.horizon?.trim() ||
    null;

  return { emoji, difficulty, durationSummary };
}

/** "Easy · 25 min" — omit empty chips. */
export function coverMetaLine(cover: GuideCover): string | null {
  const parts = [cover.difficulty, cover.durationSummary].filter(Boolean);
  return parts.length > 0 ? parts.join(' · ') : null;
}
