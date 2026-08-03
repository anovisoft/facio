import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import type { ProjectSummary } from '@/api/types';
import {
  coverMetaLine,
  resolveGuideCover,
} from '@/features/continue/coverDisplay';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = {
  guide: ProjectSummary;
  /** Soft-start paraphrase while Cover title may still be forming. */
  softStartLine?: string | null;
};

/**
 * Guide Cover — emoji, title, difficulty · duration (Facio 0.1 §7).
 * Lives on Guide page; not as Continue/drawer card twin.
 */
export function GuideCoverHeader({ guide, softStartLine }: Props) {
  const { colors } = useTheme();
  const cover = resolveGuideCover(guide);
  const title =
    guide.title || guide.outcome || guide.raw_intent || softStartLine || '';
  const meta = coverMetaLine(cover);

  return (
    <View style={styles.root}>
      <Text style={styles.emoji} accessibilityLabel={cover.emoji}>
        {cover.emoji}
      </Text>
      {title ? (
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={3}>
          {title}
        </Text>
      ) : null}
      {meta ? (
        <Text style={[styles.meta, { color: colors.textSecondary }]}>
          {meta}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    marginBottom: spacing.lg,
    gap: spacing.xs,
  },
  emoji: {
    fontSize: 40,
    lineHeight: 48,
    marginBottom: spacing.xs,
  },
  title: {
    ...typography.hero,
  },
  meta: {
    ...typography.subtitle,
    fontWeight: '500',
  },
});
