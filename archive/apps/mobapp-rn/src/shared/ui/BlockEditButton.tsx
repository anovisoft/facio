import React from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from '../../../node_modules/react-i18next';

import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  onPress: () => void;
  disabled?: boolean;
};

/**
 * Top-right Edit + pencil for a specific UI Block (checklist / stepper / …).
 * Primary Manual entry — Slice E2b-iterate #12.
 */
export function BlockEditButton({ onPress, disabled }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={t('manualEdit.editBlockA11y')}
      disabled={disabled}
      onPress={onPress}
      hitSlop={8}
      style={({ pressed }) => [
        styles.btn,
        { opacity: disabled ? 0.4 : pressed ? 0.75 : 1 },
      ]}
    >
      <Ionicons
        name="create-outline"
        size={16}
        color={colors.primary}
      />
      <Text style={[styles.label, { color: colors.primary }]}>
        {t('manualEdit.edit')}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
    paddingVertical: 2,
    paddingHorizontal: 2,
  },
  label: {
    ...typography.caption,
    fontWeight: '700',
  },
});
