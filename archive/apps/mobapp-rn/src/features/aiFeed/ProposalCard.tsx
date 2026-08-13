import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type { AiFeedProposal } from '@/features/aiFeed/types';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  proposalIndex: number;
  proposal: AiFeedProposal;
  applied?: boolean;
  disabled?: boolean;
  onReview: () => void;
};

/**
 * Append-only proposal card in Active AI Feed — summary + Diff CTA.
 * No sticky Start Guide; apply always goes through Diff confirm.
 */
export function ProposalCard({
  proposalIndex,
  proposal,
  applied,
  disabled,
  onReview,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const changeCount = proposal.diff.length;

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <Text style={[styles.version, { color: colors.textMuted }]}>
        {t('aiFeed.proposalVersion', { n: proposalIndex })}
      </Text>
      {proposal.summary ? (
        <Text style={[styles.summary, { color: colors.text }]}>
          {proposal.summary}
        </Text>
      ) : (
        <Text style={[styles.summary, { color: colors.textSecondary }]}>
          {t('aiFeed.proposalFallback')}
        </Text>
      )}
      <Text style={[styles.meta, { color: colors.textMuted }]}>
        {t('aiFeed.changeCount', { count: changeCount })}
      </Text>
      {applied ? (
        <Text style={[styles.applied, { color: colors.textSecondary }]}>
          {t('aiFeed.proposalApplied')}
        </Text>
      ) : (
        <PrimaryButton
          label={t('aiFeed.reviewChanges')}
          disabled={disabled || changeCount === 0}
          onPress={onReview}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.sm,
  },
  version: {
    ...typography.caption,
    fontWeight: '600',
  },
  summary: {
    ...typography.body,
  },
  meta: {
    ...typography.caption,
    marginBottom: spacing.xs,
  },
  applied: {
    ...typography.caption,
    fontWeight: '600',
  },
});
