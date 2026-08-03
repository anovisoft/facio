import React, { type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';

import { GlassSurface } from '@/shared/ui/GlassSurface';

/** Canonical diameter for header/menu glass chips (Continue ☰, Session ≡, drawer ⚙). */
export const GLASS_ICON_CHIP_SIZE = 40;

type Props = {
  onPress: () => void;
  accessibilityLabel: string;
  children: ReactNode;
  /** Diameter; default = GLASS_ICON_CHIP_SIZE (slightly smaller than GlassFab 58). */
  size?: number;
  /**
   * `header` — native stack headerRight: Ionicons only, no GlassSurface border
   * (avoids double outline against nav chrome). Continue/drawer keep `default`.
   */
  variant?: 'default' | 'header';
};

/** Circular liquid-glass chip for icon actions (☰, ⚙). */
export function GlassIconButton({
  onPress,
  accessibilityLabel,
  children,
  size = GLASS_ICON_CHIP_SIZE,
  variant = 'default',
}: Props) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => [pressed && styles.pressed]}
    >
      {variant === 'header' ? (
        <View style={[styles.headerHit, { width: size, height: size }]}>
          {children}
        </View>
      ) : (
        <GlassSurface
          style={{ width: size, height: size, borderRadius: size / 2 }}
        >
          <View style={styles.inner}>{children}</View>
        </GlassSurface>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  inner: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerHit: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.88,
    transform: [{ scale: 0.96 }],
  },
});
