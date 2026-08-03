import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { DayResponse } from '@/api/types';
import {
  capitalizeLabel,
  dayKindLabel,
  isGenericDayLabel,
} from '@/shared/ui/dayLabels';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  days: DayResponse[];
  /** Cap on rendered day rows — keeps the outline a glance, not a list. */
  maxRows?: number;
};

function outlineDayLabel(
  day: DayResponse,
  t: (key: string, opts?: Record<string, unknown>) => string,
): string {
  const n = day.day_index + 1;
  const kindLabel = capitalizeLabel(dayKindLabel(day.kind, t));
  const title = day.title?.trim() || null;
  // Skip redundant "Day N · Day · Title" when kind is generic "day".
  if (day.kind === 'other' || isGenericDayLabel(kindLabel)) {
    if (title && !isGenericDayLabel(title)) {
      return t('guide.dayHeader', { n, title });
    }
    return t('guide.dayOnly', { n });
  }
  const head = t('path.dayHeader', { n, kind: kindLabel });
  if (title && !isGenericDayLabel(title)) return `${head} · ${title}`;
  return head;
}

/**
 * Compact «план есть» preview: day labels + short titles only.
 * Sourced from `project.days`, which already carries gate outline titles
 * before the full Path arrives, then real day titles once it does.
 */
export function PlanOutline({ days, maxRows = 6 }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  if (days.length === 0) return null;

  const sorted = [...days].sort((a, b) => a.day_index - b.day_index);
  const shown = sorted.slice(0, maxRows);
  const hasMore = sorted.length > shown.length;

  return (
    <View style={styles.root}>
      {shown.map((day) => (
        <Text
          key={day.day_index}
          style={[styles.row, { color: colors.text }]}
          numberOfLines={1}
        >
          {outlineDayLabel(day, t)}
        </Text>
      ))}
      {hasMore ? (
        <Text style={[styles.more, { color: colors.textMuted }]}>…</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.xs,
  },
  row: {
    ...typography.body,
  },
  more: {
    ...typography.caption,
  },
});
