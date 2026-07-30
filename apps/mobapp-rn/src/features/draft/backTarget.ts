import type { StateVersionSummary } from '@/api/types';

const LLM_SOURCES = new Set(['llm_create', 'llm_refine', 'llm_repair']);

/**
 * Pick a prior LLM snapshot to restore for «Назад».
 * Skips further undo when the tip is already a user_restore (no restored_from in API).
 */
export function findBackTarget(
  versions: StateVersionSummary[],
  currentVersion: number | null | undefined,
): number | null {
  if (currentVersion == null || currentVersion <= 1) return null;

  const tip = versions.find((v) => v.version === currentVersion);
  if (tip?.source === 'user_restore') return null;

  const older = versions
    .filter((v) => v.version < currentVersion && LLM_SOURCES.has(v.source))
    .sort((a, b) => b.version - a.version);

  return older[0]?.version ?? null;
}
