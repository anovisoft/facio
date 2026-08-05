import React from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ClarifyQuestion } from '@/api/types';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const MULTI_JOIN = ', ';

function parseMultiValue(value: string | undefined): string[] {
  if (!value?.trim()) return [];
  return value
    .split(/,\s*/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function joinMulti(values: string[]): string {
  return values.join(MULTI_JOIN);
}

/** Insert or remove a chip option inside the free-form comment canvas. */
export function syncOptionIntoComment(
  comment: string,
  option: string,
  selected: boolean,
): string {
  const parts = comment
    .split(/,\s*|\n/)
    .map((s) => s.trim())
    .filter(Boolean);
  if (selected) {
    if (!parts.includes(option)) parts.push(option);
  } else {
    return parts.filter((p) => p !== option).join(MULTI_JOIN);
  }
  return parts.join(MULTI_JOIN);
}

type Props = {
  questions: ClarifyQuestion[];
  answers: Record<string, string>;
  comment: string;
  disabled: boolean;
  /** Primary refine — gated on having answers or a comment. */
  canSubmit: boolean;
  /** Skip / reveal CTA enabled. */
  canSkip: boolean;
  /** Hide skip when notes-only and plan already exists (no new inputs). */
  showSkip: boolean;
  pathWaiting: boolean;
  /** clarify_first: skip reveals Intent plan (no empty refine). */
  clarifyFirst: boolean;
  onSelectAnswer: (questionId: string, value: string) => void;
  onChangeComment: (value: string) => void;
  onSubmit: () => void;
  /**
   * clarify_first → reveal background plan;
   * after reveal → empty refine («update without answers»).
   */
  onSkip: () => void;
};

/**
 * Clarifying turn in Plan Feed: optional chips + free-form note in one block.
 * Questions-first (E2a-iterate): primary = submit answers; secondary = skip/reveal.
 */
export function PlanFeedQuestions({
  questions,
  answers,
  comment,
  disabled,
  canSubmit,
  canSkip,
  showSkip,
  pathWaiting,
  clarifyFirst,
  onSelectAnswer,
  onChangeComment,
  onSubmit,
  onSkip,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const hasQuestions = questions.length > 0;
  const hasMulti = questions.some((q) => q.selection === 'multi');
  const skipLabel = clarifyFirst
    ? t('planFeed.buildWithoutAnswers')
    : t('planFeed.updateWithoutAnswers');
  const commentPlaceholder = hasMulti
    ? t('planFeed.multiCommentPlaceholder')
    : hasQuestions
      ? t('draft.commentPlaceholder')
      : t('planFeed.composerPlaceholder');

  const onChipSelect = (question: ClarifyQuestion, option: string) => {
    if (question.selection === 'multi') {
      const current = parseMultiValue(answers[question.id]);
      const nextSelected = current.includes(option)
        ? current.filter((v) => v !== option)
        : [...current, option];
      onSelectAnswer(question.id, joinMulti(nextSelected));
      onChangeComment(
        syncOptionIntoComment(comment, option, !current.includes(option)),
      );
      return;
    }
    onSelectAnswer(question.id, option);
  };

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
      {questions.map((question, index) => {
        const mode = question.selection === 'multi' ? 'multi' : 'single';
        return (
          <View key={question.id} style={styles.questionBlock}>
            <Text style={[styles.question, { color: colors.text }]}>
              {index + 1}. {question.prompt}
            </Text>
            <ClarifyChips
              options={question.options}
              selection={mode}
              selected={mode === 'single' ? answers[question.id] ?? null : null}
              selectedValues={
                mode === 'multi'
                  ? parseMultiValue(answers[question.id])
                  : undefined
              }
              disabled={disabled}
              allowCustom={mode === 'single'}
              customPlaceholder={t('draft.freeTextPlaceholder')}
              onSelect={(option) => onChipSelect(question, option)}
            />
          </View>
        );
      })}
      {hasQuestions ? (
        <Text style={[styles.noteLabel, { color: colors.textMuted }]}>
          {hasMulti
            ? t('planFeed.multiCommentLabel')
            : t('draft.commentLabel')}
        </Text>
      ) : null}
      <TextInput
        value={comment}
        onChangeText={onChangeComment}
        editable={!disabled}
        multiline
        textAlignVertical="top"
        placeholder={commentPlaceholder}
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
      {pathWaiting && !clarifyFirst ? (
        <Text style={[styles.hint, { color: colors.textSecondary }]}>
          {t('draft.refineWaitPath')}
        </Text>
      ) : null}
      {clarifyFirst && pathWaiting ? (
        <Text style={[styles.hint, { color: colors.textSecondary }]}>
          {t('planFeed.clarifyFirstHint')}
        </Text>
      ) : null}
      <PrimaryButton
        variant="secondary"
        label={t('draft.refine')}
        disabled={!canSubmit}
        onPress={onSubmit}
      />
      {showSkip ? (
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
      ) : null}
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
  // Avoid typography.body.lineHeight on multiline TextInput — iOS misaligns
  // the caret/text when typing starts (#11). Match Manual checklist pattern.
  input: {
    fontSize: typography.body.fontSize,
    fontWeight: typography.body.fontWeight,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.md,
    minHeight: 64,
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
