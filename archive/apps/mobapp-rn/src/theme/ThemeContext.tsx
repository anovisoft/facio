import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from 'react';
import { Appearance, useColorScheme } from 'react-native';

import {
  darkColors,
  lightColors,
  type ColorPalette,
  type ThemeMode,
} from '@/theme/index';

interface ThemeContextValue {
  colors: ColorPalette;
  effectiveTheme: 'light' | 'dark';
  themeMode: ThemeMode;
}

export type { ThemeMode };

const ThemeContext = createContext<ThemeContextValue>({
  colors: lightColors,
  effectiveTheme: 'light',
  themeMode: 'system',
});

type Props = {
  themeMode: ThemeMode;
  children: ReactNode;
};

export function ThemeProvider({ themeMode, children }: Props) {
  const systemScheme = useColorScheme();

  const effectiveTheme = useMemo<'light' | 'dark'>(() => {
    if (themeMode === 'system') {
      return systemScheme === 'dark' ? 'dark' : 'light';
    }
    return themeMode;
  }, [themeMode, systemScheme]);

  /**
   * Sync RN/UIKit color scheme with in-app theme.
   * Without this, native-stack back button (iOS liquid glass) follows
   * system light appearance while RN content is already dark → white flash.
   */
  useEffect(() => {
    if (themeMode === 'system') {
      Appearance.setColorScheme(null);
    } else {
      Appearance.setColorScheme(themeMode);
    }
  }, [themeMode]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      colors: effectiveTheme === 'dark' ? darkColors : lightColors,
      effectiveTheme,
      themeMode,
    }),
    [effectiveTheme, themeMode],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
