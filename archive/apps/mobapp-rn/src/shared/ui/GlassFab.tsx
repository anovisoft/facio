import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from '../../../node_modules/react-i18next';

import { GlassSurface } from '@/shared/ui/GlassSurface';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

const SIZE = 58;

type Props = {
  onPress: () => void;
};

/** Floating glass «+» — new project / Intent. */
export function GlassFab({ onPress }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View
      pointerEvents="box-none"
      style={[
        styles.wrap,
        { bottom: Math.max(insets.bottom, spacing.md) + spacing.sm },
      ]}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={t('projects.newGoal')}
        onPress={onPress}
        style={({ pressed }) => [pressed && styles.pressed]}
      >
        <GlassSurface style={styles.glass}>
          <View style={styles.inner}>
            <Text style={[styles.plus, { color: colors.fabIcon }]}>+</Text>
          </View>
        </GlassSurface>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: 'absolute',
    right: spacing.lg,
    zIndex: 20,
  },
  glass: {
    width: SIZE,
    height: SIZE,
    borderRadius: SIZE / 2,
  },
  inner: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  plus: {
    ...typography.hero,
    fontSize: 32,
    lineHeight: 36,
    fontWeight: '500',
    marginTop: -2,
  },
  pressed: {
    opacity: 0.88,
    transform: [{ scale: 0.96 }],
  },
});
