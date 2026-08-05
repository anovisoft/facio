import React from 'react';
import { StyleSheet, Text, TextInput, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ClarifyQuestion } from '@/api/types';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  questions: ClarifyQuestion[];
  answers: Record<string, string>;
  comment: string;
  disabled: boolean;
  canSubmit: boolean;
  pathWaiting: boolean;
  onSelectAnswer: (questionId: string, value: string) => void;
  onChangeComment: (value: string) => void;
  onSubmit: () => void;
};

/**
 * Clarifying turn in Plan Feed: optional chips + free-form note in one block.
 * Answers are never required — free-form alone can drive refine.
 */
export function PlanFeedQuestions({
  questions,
  answers,
  comment,
  disabled,
  canSubmit,
  pathWaiting,
  onSelectAnswer,
  onChangeComment,
  onSubmit,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const hasQuestions = questions.length > 0;

  return (
    <View
      style={[
        styles.wrap,
        { backgroundColor: colors.surfaceMuted, borderColor: colors.border },
      ]}
    >
      <Text style={[styles.label, { color: colors.textMuted }]}>
        {hasQuestions
          ? t('draft.clarifyLabel')
          : t('planFeed.composerLabel')}
      </Text>
      {questions.map((question, index) => (
        <View key={question.id} style={styles.questionBlock}>
          <Text style={[styles.question, { color: colors.text }]}>
            {index + 1}. {question.prompt}
          </Text>
          <ClarifyChips
            options={question.options}
            selected={answers[question.id] ?? null}
            disabled={disabled}
            allowCustom
            customPlaceholder={t('draft.freeTextPlaceholder')}
            onSelect={(option) => onSelectAnswer(question.id, option)}
          />
        </View>
      ))}
      {hasQuestions ? (
        <Text style={[styles.noteLabel, { color: colors.textMuted }]}>
          {t('draft.commentLabel')}
        </Text>
      ) : null}
      <TextInput
        value={comment}
        onChangeText={onChangeComment}
        editable={!disabled}
        multiline
        placeholder={t('draft.commentPlaceholder')}
        placeholderTextColor={colors.textMuted}
        style={[
          styles.input,
          {
            color: colors.text,
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}
      />
      {pathWaiting ? (
        <Text style={[styles.hint, { color: colors.textSecondary }]}>
          {t('draft.refineWaitPath')}
        </Text>
      ) : null}
      <PrimaryButton
        variant="secondary"
        label={t('draft.refine')}
        disabled={!canSubmit}
        onPress={onSubmit}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.md,
    padding: spacing.md,
    gap: spacing.md,
  },
  label: {
    ...typography.label,
  },
  questionBlock: {
    gap: spacing.sm,
  },
  question: {
    ...typography.subtitle,
  },
  noteLabel: {
    ...typography.label,
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    minHeight: 64,
    textAlignVertical: 'top',
  },
  hint: {
    ...typography.caption,
  },
});
