import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type {
  ActionResponse,
  ChecklistItemResponse,
  GroupResponse,
} from '@/api/types';
import { ChecklistList } from '@/shared/ui/ChecklistList';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  groups: GroupResponse[];
  actions: ActionResponse[];
  /** Draft preview: titles first; expand for detail. */
  compact?: boolean;
  /** Path screen: tap step to expand detail / checklist. */
  expandable?: boolean;
  checklistDisabled?: boolean;
  onToggleChecklist?: (
    item: ChecklistItemResponse,
    nextDone: boolean,
  ) => void;
};

type Section = {
  key: string;
  title: string | null;
  description: string | null;
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
    sections.push({
      key: group.id,
      title: group.title,
      description: group.description ?? null,
      actions: list,
    });
    byGroup.delete(group.id);
    byGroup.delete(group.key);
  }

  for (const [key, list] of byGroup) {
    sections.push({
      key,
      title: list[0]?.group_title ?? null,
      description: null,
      actions: list,
    });
  }

  if (ungrouped.length > 0) {
    sections.push({
      key: '_ungrouped',
      title: null,
      description: null,
      actions: ungrouped,
    });
  }

  return sections;
}

function statusLabel(
  status: ActionResponse['status'],
  t: (key: string) => string,
): string | null {
  switch (status) {
    case 'done':
      return t('path.statusDone');
    case 'skipped':
      return t('path.statusSkipped');
    case 'pending':
      return null;
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

export function PathList({
  groups,
  actions,
  compact = false,
  expandable = false,
  checklistDisabled,
  onToggleChecklist,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [expanded, setExpanded] = useState(!compact);
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});
  const sections = buildSections(groups, actions);
  const showDetail = !compact || expanded;

  if (actions.length === 0) {
    return null;
  }

  const toggleOpen = (id: string) => {
    setOpenIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

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
            {section.description ? (
              <Text
                style={[styles.groupDescription, { color: colors.textSecondary }]}
              >
                {section.description}
              </Text>
            ) : null}
            {section.actions.map((action, index) => {
              const status = statusLabel(action.status, t);
              const isOpen = expandable
                ? Boolean(openIds[action.id])
                : true;
              const canExpand =
                expandable &&
                Boolean(
                  action.detail ||
                    action.why ||
                    action.checklist_items.length > 0,
                );

              return (
                <View
                  key={action.id}
                  style={[
                    styles.step,
                    {
                      backgroundColor: colors.surface,
                      borderColor: colors.border,
                      opacity: action.status === 'pending' ? 1 : 0.72,
                    },
                  ]}
                >
                  <Pressable
                    disabled={!canExpand}
                    onPress={() => toggleOpen(action.id)}
                  >
                    <View style={styles.stepHeader}>
                      <Text
                        style={[styles.stepTitle, { color: colors.text, flex: 1 }]}
                      >
                        {index + 1}. {action.title}
                      </Text>
                      {status ? (
                        <Text
                          style={[
                            styles.status,
                            { color: colors.textSecondary },
                          ]}
                        >
                          {status}
                        </Text>
                      ) : null}
                    </View>
                    {action.estimate_min != null ? (
                      <Text
                        style={[styles.meta, { color: colors.textSecondary }]}
                      >
                        {t('common.minutes', { count: action.estimate_min })}
                      </Text>
                    ) : null}
                    {canExpand ? (
                      <Text
                        style={[styles.toggle, { color: colors.primary }]}
                      >
                        {isOpen
                          ? t('path.collapseStep')
                          : t('path.expandStep')}
                      </Text>
                    ) : null}
                  </Pressable>

                  {isOpen ? (
                    <View style={styles.expanded}>
                      {action.why ? (
                        <Text
                          style={[styles.detail, { color: colors.textSecondary }]}
                        >
                          {action.why}
                        </Text>
                      ) : null}
                      {action.detail ? (
                        <Text
                          style={[styles.detail, { color: colors.textSecondary }]}
                        >
                          {action.detail}
                        </Text>
                      ) : null}
                      {action.checklist_items.length > 0 ? (
                        <ChecklistList
                          items={action.checklist_items}
                          disabled={
                            checklistDisabled || action.status !== 'pending'
                          }
                          onToggle={
                            onToggleChecklist && action.status === 'pending'
                              ? onToggleChecklist
                              : undefined
                          }
                        />
                      ) : null}
                    </View>
                  ) : null}
                </View>
              );
            })}
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
  groupDescription: {
    ...typography.caption,
    marginBottom: spacing.sm,
  },
  step: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    gap: spacing.xs,
  },
  stepHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  stepTitle: {
    ...typography.subtitle,
  },
  status: {
    ...typography.caption,
  },
  meta: {
    ...typography.caption,
  },
  detail: {
    ...typography.body,
  },
  expanded: {
    marginTop: spacing.sm,
    gap: spacing.sm,
  },
  toggle: {
    ...typography.caption,
    marginTop: spacing.xs,
  },
});
