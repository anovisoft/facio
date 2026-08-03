import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ProjectSummary } from '@/api/types';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  guide: ProjectSummary;
};

/**
 * Contract glance on Guide — result, success criteria, horizon.
 * Pre-commit trust layer (Commitment = sticky CTA, not a duplicate map).
 */
export function GuideContractGlance({ guide }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  const result = guide.outcome || guide.paraphrase || null;
  const success = guide.success_criteria?.trim() || null;
  const horizon = guide.horizon?.trim() || guide.cover_duration_summary?.trim() || null;

  if (!result && !success && !horizon) return null;

  return (
    <View style={styles.root}>
      {result ? (
        <View style={styles.block}>
          <Text style={[styles.label, { color: colors.textMuted }]}>
            {t('guide.result')}
          </Text>
          <Text style={[styles.body, { color: colors.text }]}>{result}</Text>
        </View>
      ) : null}
      {success ? (
        <View style={styles.block}>
          <Text style={[styles.label, { color: colors.textMuted }]}>
            {t('guide.success')}
          </Text>
          <Text style={[styles.body, { color: colors.text }]}>{success}</Text>
        </View>
      ) : null}
      {horizon ? (
        <View style={styles.block}>
          <Text style={[styles.label, { color: colors.textMuted }]}>
            {t('guide.horizon')}
          </Text>
          <Text style={[styles.body, { color: colors.text }]}>{horizon}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.md,
    marginBottom: spacing.lg,
  },
  block: {
    gap: spacing.xs,
  },
  label: {
    ...typography.label,
  },
  body: {
    ...typography.body,
  },
});
