import React, { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { CompactRoadmap } from '@/features/guide/CompactRoadmap';
import { GuideContractGlance } from '@/features/guide/GuideContractGlance';
import { GuideCoverHeader } from '@/features/guide/GuideCoverHeader';
import type { PlanSnapshot } from '@/features/guide/planFeed/types';
import { PathList } from '@/shared/ui/PathList';
import { PlanOutline } from '@/shared/ui/PlanOutline';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  planIndex: number;
  snapshot: PlanSnapshot;
  committing: boolean;
  disabled: boolean;
  onStart: () => void;
  onSaveWithoutStarting?: () => void;
};

/**
 * Versioned plan card in Create Plan Feed — Cover + contract + roadmap + Start CTA.
 */
export function PlanFeedPlanCard({
  planIndex,
  snapshot,
  committing,
  disabled,
  onStart,
  onSaveWithoutStarting,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [detailExpanded, setDetailExpanded] = useState(false);

  const guideForCover = {
    id: `plan-v${planIndex}`,
    status: 'draft' as const,
    raw_intent: snapshot.raw_intent,
    title: snapshot.title,
    summary: snapshot.summary,
    outcome: snapshot.outcome,
    paraphrase: snapshot.paraphrase,
    success_criteria: snapshot.success_criteria,
    horizon: snapshot.horizon,
    domain: snapshot.domain,
    tags: snapshot.tags,
    cover_emoji: snapshot.cover_emoji,
    cover_difficulty: snapshot.cover_difficulty,
    cover_duration_summary: snapshot.cover_duration_summary,
    created_at: '',
    updated_at: '',
  };

  const canStart = snapshot.pathReady && !snapshot.pathError && !disabled;

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <Text style={[styles.version, { color: colors.textMuted }]}>
        {t('planFeed.planVersion', { n: planIndex })}
      </Text>

      <GuideCoverHeader guide={guideForCover} />
      <GuideContractGlance guide={guideForCover} />

      {!snapshot.pathReady && !snapshot.pathError ? (
        <View style={styles.loadingBlock}>
          <PlanOutline days={snapshot.days} />
          <View style={styles.loadingRow}>
            <ActivityIndicator color={colors.primary} />
            <Text
              style={[styles.muted, { color: colors.textSecondary, flex: 1 }]}
            >
              {t('draft.pathLoading')}
            </Text>
          </View>
        </View>
      ) : null}

      {snapshot.pathError ? (
        <Text style={[styles.error, { color: colors.error }]}>
          {t('draft.pathError')}
        </Text>
      ) : null}

      {snapshot.pathReady ? (
        <View style={styles.roadmapBlock}>
          <CompactRoadmap actions={snapshot.actions} days={snapshot.days} />
          <Pressable
            onPress={() => setDetailExpanded((v) => !v)}
            hitSlop={8}
          >
            <Text style={[styles.toggle, { color: colors.primary }]}>
              {detailExpanded
                ? t('guide.hideDetail')
                : t('guide.viewDetail')}
            </Text>
          </Pressable>
          {detailExpanded ? (
            <View style={styles.fullPlan}>
              <PathList
                groups={snapshot.groups}
                actions={snapshot.actions}
                days={snapshot.days}
                cycle={snapshot.cycle}
                expandable
                pluginsInteractive={false}
              />
            </View>
          ) : null}
        </View>
      ) : null}

      <PrimaryButton
        label={t('guide.startGuide')}
        disabled={!canStart}
        loading={committing}
        onPress={onStart}
      />
      {onSaveWithoutStarting ? (
        <Pressable
          accessibilityRole="button"
          disabled={!canStart}
          onPress={onSaveWithoutStarting}
          hitSlop={8}
          style={styles.saveLink}
        >
          <Text
            style={[
              styles.saveLinkText,
              {
                color: canStart ? colors.textSecondary : colors.textMuted,
              },
            ]}
          >
            {t('draft.saveWithoutStarting')}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.sm,
    overflow: 'visible',
    alignSelf: 'stretch',
  },
  version: {
    ...typography.label,
    fontWeight: '700',
  },
  loadingBlock: {
    gap: spacing.sm,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  muted: {
    ...typography.caption,
  },
  error: {
    ...typography.caption,
  },
  roadmapBlock: {
    gap: spacing.xs,
  },
  toggle: {
    ...typography.caption,
    fontWeight: '600',
    marginTop: spacing.xs,
  },
  fullPlan: {
    marginTop: spacing.sm,
  },
  saveLink: {
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  saveLinkText: {
    ...typography.caption,
    fontWeight: '600',
  },
});
