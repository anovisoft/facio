import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type { ActionResponse, DayResponse } from '@/api/types';
import {
  buildCompactRoadmap,
  type CompactRoadmapStatus,
} from '@/features/guide/buildCompactRoadmap';
import { isGenericDayLabel } from '@/shared/ui/dayLabels';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  actions: ActionResponse[];
  days: DayResponse[];
};

const STATUS_MARK: Record<CompactRoadmapStatus, string> = {
  done: '☑',
  pending: '○',
  skipped: '–',
  locked: '○',
};

/**
 * Guide roadmap as Compact Summaries (Facio 0.1 §9) —
 * title + status among many Sessions; grasp path in ~5s.
 */
export function CompactRoadmap({ actions, days }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const rows = buildCompactRoadmap(actions, days);

  if (rows.length === 0) return null;

  return (
    <View style={styles.root}>
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('guide.roadmapLabel')}
      </Text>
      {rows.map((row) => {
        const dayLabel =
          row.dayIndex != null
            ? row.dayTitle && !isGenericDayLabel(row.dayTitle)
              ? t('guide.dayHeader', {
                  n: row.dayIndex + 1,
                  title: row.dayTitle,
                })
              : t('guide.dayOnly', { n: row.dayIndex + 1 })
            : null;
        return (
          <View key={row.key}>
            {dayLabel ? (
              <Text
                style={[styles.dayLabel, { color: colors.textSecondary }]}
                numberOfLines={1}
              >
                {dayLabel}
              </Text>
            ) : null}
            <View style={styles.row}>
              <Text
                style={[
                  styles.mark,
                  {
                    color:
                      row.status === 'done'
                        ? colors.success
                        : row.status === 'locked' || row.status === 'skipped'
                          ? colors.textMuted
                          : colors.text,
                  },
                ]}
              >
                {STATUS_MARK[row.status]}
              </Text>
              <Text
                style={[
                  styles.title,
                  {
                    color:
                      row.status === 'locked' || row.status === 'skipped'
                        ? colors.textMuted
                        : colors.text,
                  },
                ]}
                numberOfLines={2}
              >
                {row.title}
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.xs,
  },
  sectionLabel: {
    ...typography.label,
    marginBottom: spacing.sm,
  },
  dayLabel: {
    ...typography.caption,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
    paddingVertical: 2,
  },
  mark: {
    ...typography.body,
    width: 22,
    textAlign: 'center',
  },
  title: {
    ...typography.body,
    flex: 1,
  },
});
