import React, { type ReactNode } from 'react';
import {
  Platform,
  StyleSheet,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { BlurView } from 'expo-blur';

import { useTheme } from '@/theme/ThemeContext';

type LiquidGlassModule = {
  LiquidGlassView: React.ComponentType<{
    style?: StyleProp<ViewStyle>;
    interactive?: boolean;
    effect?: 'clear' | 'regular' | 'none';
    colorScheme?: 'light' | 'dark' | 'system';
    children?: ReactNode;
  }>;
  isLiquidGlassSupported: boolean;
};

function loadLiquidGlass(): LiquidGlassModule | null {
  try {
    // Native-only; missing in Expo Go / Android / old iOS.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    return require('@callstack/liquid-glass') as LiquidGlassModule;
  } catch {
    return null;
  }
}

const liquidGlass = loadLiquidGlass();

type Props = {
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
  interactive?: boolean;
  effect?: 'clear' | 'regular';
};

/**
 * iOS 26 liquid glass when available; BlurView / translucent fallback otherwise.
 * @see https://github.com/callstack/liquid-glass
 */
export function GlassSurface({
  children,
  style,
  interactive = true,
  effect = 'regular',
}: Props) {
  const { effectiveTheme, colors } = useTheme();

  if (
    Platform.OS === 'ios' &&
    liquidGlass?.isLiquidGlassSupported &&
    liquidGlass.LiquidGlassView
  ) {
    const Glass = liquidGlass.LiquidGlassView;
    return (
      <Glass
        style={style}
        interactive={interactive}
        effect={effect}
        colorScheme={effectiveTheme}
      >
        {children}
      </Glass>
    );
  }

  return (
    <View style={[styles.fallbackShell, { borderColor: colors.border }, style]}>
      {Platform.OS === 'web' ? (
        <View
          style={[
            StyleSheet.absoluteFill,
            { backgroundColor: colors.fabFallback },
          ]}
        />
      ) : (
        <BlurView
          intensity={56}
          tint={effectiveTheme === 'dark' ? 'dark' : 'light'}
          style={StyleSheet.absoluteFill}
        />
      )}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  fallbackShell: {
    overflow: 'hidden',
    borderWidth: StyleSheet.hairlineWidth,
  },
});
