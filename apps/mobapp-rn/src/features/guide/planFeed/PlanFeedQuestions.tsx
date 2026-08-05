import React from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
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
  /** Primary refine — gated on having answers or a comment. */
  canSubmit: boolean;
  /** Skip CTA — available whenever refine is not busy / pathError. */
  canSkip: boolean;
  pathWaiting: boolean;
  onSelectAnswer: (questionId: string, value: string) => void;
  onChangeComment: (value: string) => void;
  onSubmit: () => void;
  /** Refine with empty answers + empty comment (build/update without answers). */
  onSkip: () => void;
};

/**
 * Clarifying turn in Plan Feed: optional chips + free-form note in one block.
 * Answers are never required — free-form alone can drive refine; skip CTA
 * always offers build/update without answering (#9).
 */
export function PlanFeedQuestions({
  questions,
  answers,
  comment,
  disabled,
  canSubmit,
  canSkip,
  pathWaiting,
  onSelectAnswer,
  onChangeComment,
  onSubmit,
  onSkip,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const hasQuestions = questions.length > 0;
  const skipLabel = pathWaiting
    ? t('planFeed.buildWithoutAnswers')
    : t('planFeed.updateWithoutAnswers');

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
      <Pressable
        accessibilityRole="button"
        disabled={!canSkip}
        onPress={onSkip}
        hitSlop={8}
        style={styles.skipLink}
      >
        <Text
          style={[
            styles.skipLinkText,
            {
              color: canSkip ? colors.textSecondary : colors.textMuted,
            },
          ]}
        >
          {skipLabel}
        </Text>
      </Pressable>
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
  skipLink: {
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  skipLinkText: {
    ...typography.caption,
    fontWeight: '600',
  },
});
