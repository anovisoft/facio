import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { buildZustandStorage } from '@/services/storage';
import type { ThemeMode } from '@/theme';

interface SessionState {
  /** Last focused project for beacons / resume hints. */
  lastProjectId: string | null;
  setLastProjectId: (id: string | null) => void;
  /** Appearance: system (default) | light | dark. */
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
  /** Project ids that already showed the First Completion beat. */
  firstCompletionShown: Record<string, true>;
  hasFirstCompletionShown: (projectId: string) => boolean;
  markFirstCompletionShown: (projectId: string) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      lastProjectId: null,
      setLastProjectId: (id) => set({ lastProjectId: id }),
      themeMode: 'system',
      setThemeMode: (mode) => set({ themeMode: mode }),
      firstCompletionShown: {},
      hasFirstCompletionShown: (projectId) =>
        Boolean(get().firstCompletionShown[projectId]),
      markFirstCompletionShown: (projectId) =>
        set((state) => ({
          firstCompletionShown: {
            ...state.firstCompletionShown,
            [projectId]: true,
          },
        })),
    }),
    {
      name: 'facio-session',
      storage: createJSONStorage(() => buildZustandStorage('facio-session')),
      partialize: (state) => ({
        lastProjectId: state.lastProjectId,
        themeMode: state.themeMode,
        firstCompletionShown: state.firstCompletionShown,
      }),
    },
  ),
);
