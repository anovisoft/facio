import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  why: string;
};

/**
 * “Why today” support copy — demoted below Full Block on Session
 * (Slice D layout: title → day → Block → detail / why).
 */
export function WhyHero({ why }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const trimmed = why.trim();
  if (!trimmed) return null;

  return (
    <View style={styles.root}>
      <Text style={[styles.label, { color: colors.textMuted }]}>
        {t('home.whyNow')}
      </Text>
      <Text style={[styles.why, { color: colors.textSecondary }]}>
        {trimmed}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    marginTop: spacing.md,
    gap: spacing.xs,
  },
  label: {
    ...typography.label,
    textTransform: 'uppercase',
  },
  why: {
    ...typography.body,
  },
});
