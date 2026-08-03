import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { getLocalDate } from '@/services/localDate';
import { buildZustandStorage } from '@/services/storage';
import type { ThemeMode } from '@/theme';

/**
 * Ephemeral Full Block runtime for same-calendar-day resume (D2).
 * Counter values stay server-backed; this stores position / clocks only.
 * Cross-day: treated as expired — next open starts fresh beat index.
 */
export type BlockRuntimeRest = {
  beatId: string;
  startedAt: number;
  durationSec: number;
};

export type BlockRuntimeEntry = {
  /** Device local YYYY-MM-DD when last written. */
  localDate: string;
  beatIndex: number;
  sessionDone?: boolean;
  rest?: BlockRuntimeRest | null;
};

interface SessionState {
  /** Last focused project for beacons / resume hints. */
  lastProjectId: string | null;
  setLastProjectId: (id: string | null) => void;
  /** Appearance: system (default) | light | dark. */
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  /**
   * In-progress Block runtime keyed by actionId.
   * Valid only when entry.localDate === today's local date (D2).
   */
  blockRuntimeByActionId: Record<string, BlockRuntimeEntry>;
  /** Returns entry if same local day; otherwise clears stale and returns null. */
  getBlockRuntime: (actionId: string) => BlockRuntimeEntry | null;
  setBlockRuntime: (
    actionId: string,
    patch: Omit<BlockRuntimeEntry, 'localDate'> & { localDate?: string },
  ) => void;
  clearBlockRuntime: (actionId: string) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      lastProjectId: null,
      setLastProjectId: (id) => set({ lastProjectId: id }),
      themeMode: 'system',
      setThemeMode: (mode) => set({ themeMode: mode }),
      blockRuntimeByActionId: {},
      getBlockRuntime: (actionId) => {
        const entry = get().blockRuntimeByActionId[actionId];
        if (!entry) return null;
        const today = getLocalDate();
        if (entry.localDate !== today) {
          set((state) => {
            const next = { ...state.blockRuntimeByActionId };
            delete next[actionId];
            return { blockRuntimeByActionId: next };
          });
          return null;
        }
        return entry;
      },
      setBlockRuntime: (actionId, patch) => {
        const localDate = patch.localDate ?? getLocalDate();
        set((state) => ({
          blockRuntimeByActionId: {
            ...state.blockRuntimeByActionId,
            [actionId]: {
              localDate,
              beatIndex: patch.beatIndex,
              sessionDone: patch.sessionDone,
              rest: patch.rest ?? null,
            },
          },
        }));
      },
      clearBlockRuntime: (actionId) =>
        set((state) => {
          if (!(actionId in state.blockRuntimeByActionId)) return state;
          const next = { ...state.blockRuntimeByActionId };
          delete next[actionId];
          return { blockRuntimeByActionId: next };
        }),
    }),
    {
      name: 'facio-session',
      storage: createJSONStorage(() => buildZustandStorage('facio-session')),
      partialize: (state) => ({
        lastProjectId: state.lastProjectId,
        themeMode: state.themeMode,
        blockRuntimeByActionId: state.blockRuntimeByActionId,
      }),
    },
  ),
);
