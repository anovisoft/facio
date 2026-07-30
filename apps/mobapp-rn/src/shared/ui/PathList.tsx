import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ActionResponse, GroupResponse } from '@/api/types';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  groups: GroupResponse[];
  actions: ActionResponse[];
  /** Draft preview: titles first; expand for detail. */
  compact?: boolean;
};

type Section = {
  key: string;
  title: string | null;
  actions: ActionResponse[];
};

function buildSections(
  groups: GroupResponse[],
  actions: ActionResponse[],
): Section[] {
  const sortedGroups = [...groups].sort((a, b) => a.sort - b.sort);
  const sortedActions = [...actions].sort((a, b) => a.sort - b.sort);
  const byGroup = new Map<string, ActionResponse[]>();
  const ungrouped: ActionResponse[] = [];

  for (const action of sortedActions) {
    const key = action.group_id ?? action.group_key;
    if (!key) {
      ungrouped.push(action);
      continue;
    }
    const list = byGroup.get(key) ?? [];
    list.push(action);
    byGroup.set(key, list);
  }

  const sections: Section[] = [];
  for (const group of sortedGroups) {
    const list = byGroup.get(group.id) ?? byGroup.get(group.key) ?? [];
    if (list.length === 0) continue;
    sections.push({ key: group.id, title: group.title, actions: list });
    byGroup.delete(group.id);
    byGroup.delete(group.key);
  }

  for (const [key, list] of byGroup) {
    sections.push({
      key,
      title: list[0]?.group_title ?? null,
      actions: list,
    });
  }

  if (ungrouped.length > 0) {
    sections.push({ key: '_ungrouped', title: null, actions: ungrouped });
  }

  return sections;
}

export function PathList({ groups, actions, compact = false }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [expanded, setExpanded] = useState(!compact);
  const sections = buildSections(groups, actions);
  const showDetail = !compact || expanded;

  if (actions.length === 0) {
    return null;
  }

  return (
    <View style={styles.root}>
      {!showDetail ? (
        <View style={styles.preview}>
          {actions
            .slice()
            .sort((a, b) => a.sort - b.sort)
            .slice(0, 3)
            .map((action, index) => (
              <Text
                key={action.id}
                style={[styles.previewRow, { color: colors.text }]}
                numberOfLines={1}
              >
                {index + 1}. {action.title}
              </Text>
            ))}
          {actions.length > 3 ? (
            <Text style={[styles.more, { color: colors.textMuted }]}>…</Text>
          ) : null}
        </View>
      ) : (
        sections.map((section) => (
          <View key={section.key} style={styles.section}>
            {section.title ? (
              <Text style={[styles.groupTitle, { color: colors.textMuted }]}>
                {section.title}
              </Text>
            ) : null}
            {section.actions.map((action, index) => (
              <View
                key={action.id}
                style={[
                  styles.step,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                  },
                ]}
              >
                <Text style={[styles.stepTitle, { color: colors.text }]}>
                  {index + 1}. {action.title}
                </Text>
                {action.estimate_min != null ? (
                  <Text style={[styles.meta, { color: colors.textSecondary }]}>
                    {t('common.minutes', { count: action.estimate_min })}
                  </Text>
                ) : null}
                {action.detail ? (
                  <Text style={[styles.detail, { color: colors.textSecondary }]}>
                    {action.detail}
                  </Text>
                ) : null}
              </View>
            ))}
          </View>
        ))
      )}

      {compact ? (
        <Pressable onPress={() => setExpanded((v) => !v)} hitSlop={8}>
          <Text style={[styles.toggle, { color: colors.primary }]}>
            {expanded ? t('draft.collapsePath') : t('draft.expandPath')}
          </Text>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.sm,
  },
  preview: {
    gap: spacing.xs,
  },
  previewRow: {
    ...typography.body,
  },
  more: {
    ...typography.caption,
  },
  section: {
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  groupTitle: {
    ...typography.label,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  step: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    gap: spacing.xs,
  },
  stepTitle: {
    ...typography.subtitle,
  },
  meta: {
    ...typography.caption,
  },
  detail: {
    ...typography.body,
    marginTop: spacing.xs,
  },
  toggle: {
    ...typography.caption,
    marginTop: spacing.xs,
  },
});
