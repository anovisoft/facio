import React from 'react';
import { StyleSheet, Text } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { RootScreenProps } from '@/navigation/types';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

export function InstantAnswerScreen({
  route,
}: RootScreenProps<'InstantAnswer'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { payload } = route.params;
  return (
    <SafeScreen scroll>
      <Text style={[styles.label, { color: colors.textMuted }]}>
        {payload.label}
      </Text>
      <Text style={[styles.answer, { color: colors.text }]}>
        {payload.answer}
      </Text>
      <Text style={[styles.cta, { color: colors.text }]}>
        {t('instantAnswer.cta')}
      </Text>
      {payload.goal_suggestions.map((goal) => (
        <Text
          key={goal}
          style={[
            styles.chip,
            {
              color: colors.primary,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
        >
          {goal}
        </Text>
      ))}
      <Text style={[styles.note, { color: colors.textMuted }]}>
        {t('common.placeholder')}
      </Text>
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  label: {
    ...typography.caption,
    marginBottom: spacing.sm,
  },
  answer: {
    ...typography.body,
    marginBottom: spacing.lg,
  },
  cta: {
    ...typography.subtitle,
    marginBottom: spacing.md,
  },
  chip: {
    ...typography.body,
    borderWidth: 1,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  note: {
    ...typography.caption,
    marginTop: spacing.lg,
  },
});
