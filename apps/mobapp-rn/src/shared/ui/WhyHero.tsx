import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  why: string;
};

/** Hero «Почему сейчас» — must be prominent, never a grey footnote. */
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
      <Text style={[styles.why, { color: colors.text }]}>{trimmed}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  label: {
    ...typography.label,
    textTransform: 'uppercase',
  },
  why: {
    ...typography.title,
    lineHeight: 30,
  },
});
