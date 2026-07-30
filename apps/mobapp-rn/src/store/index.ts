import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import { buildZustandStorage } from '@/services/storage';
import type { ThemeMode } from '@/theme/ThemeContext';

interface SessionState {
  /** Last focused project for beacons / resume hints. */
  lastProjectId: string | null;
  setLastProjectId: (id: string | null) => void;
  /** Appearance: system (default) | light | dark. */
  themeMode: ThemeMode;
  setThemeMode: (mode: ThemeMode) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      lastProjectId: null,
      setLastProjectId: (id) => set({ lastProjectId: id }),
      themeMode: 'system',
      setThemeMode: (mode) => set({ themeMode: mode }),
    }),
    {
      name: 'facio-session',
      storage: createJSONStorage(() => buildZustandStorage('facio-session')),
      partialize: (state) => ({
        lastProjectId: state.lastProjectId,
        themeMode: state.themeMode,
      }),
    },
  ),
);
