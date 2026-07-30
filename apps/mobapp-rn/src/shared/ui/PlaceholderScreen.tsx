import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  title: string;
  subtitle?: string;
};

/** Temporary shell for screens implemented in S2/S3. */
export function PlaceholderScreen({ title, subtitle }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  return (
    <SafeScreen>
      <Text style={[styles.title, { color: colors.text }]}>{title}</Text>
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
        {subtitle ?? t('common.placeholder')}
      </Text>
      <View style={[styles.rule, { backgroundColor: colors.border }]} />
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  title: {
    ...typography.title,
    marginBottom: spacing.sm,
  },
  subtitle: {
    ...typography.body,
  },
  rule: {
    marginTop: spacing.lg,
    height: 1,
  },
});
