import React, { type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { GlassSurface } from '@/shared/ui/GlassSurface';
import { useTheme } from '@/theme/ThemeContext';

/** Canonical diameter for header/menu glass chips (Continue ☰, Session ≡, drawer ⚙). */
export const GLASS_ICON_CHIP_SIZE = 40;

type Props = {
  onPress: () => void;
  accessibilityLabel: string;
  children: ReactNode;
  /** Diameter; default = GLASS_ICON_CHIP_SIZE (slightly smaller than GlassFab 58). */
  size?: number;
  /**
   * `default` — LiquidGlass / BlurView round chip (in-content: Continue ☰).
   * `nav` — plain circular chip for native stack header (no LiquidGlass — avoids
   *   double outline with iOS 26 system header chrome).
   * `header` — Ionicons only, no chip shell (legacy).
   */
  variant?: 'default' | 'nav' | 'header';
};

/** Circular icon chip — liquid glass in content; plain circle in stack headers. */
export function GlassIconButton({
  onPress,
  accessibilityLabel,
  children,
  size = GLASS_ICON_CHIP_SIZE,
  variant = 'default',
}: Props) {
  const { colors } = useTheme();
  const square = {
    width: size,
    height: size,
    borderRadius: size / 2,
  } as const;

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => [
        { width: size, height: size, overflow: 'hidden' as const },
        pressed && styles.pressed,
      ]}
    >
      {variant === 'header' ? (
        <View style={[styles.center, square]}>{children}</View>
      ) : variant === 'nav' ? (
        <View
          style={[
            styles.center,
            styles.navChip,
            square,
            {
              backgroundColor: colors.fabFallback,
              borderColor: colors.border,
            },
          ]}
        >
          {children}
        </View>
      ) : (
        <GlassSurface style={square}>
          <View style={styles.center}>{children}</View>
        </GlassSurface>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  navChip: {
    borderWidth: StyleSheet.hairlineWidth,
  },
  pressed: {
    opacity: 0.88,
    transform: [{ scale: 0.96 }],
  },
});
