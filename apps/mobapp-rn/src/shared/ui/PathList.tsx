import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type {
  ActionResponse,
  ChecklistItemResponse,
  CycleResponse,
  DayKind,
  DayResponse,
  GroupResponse,
} from '@/api/types';
import { ChecklistList } from '@/shared/ui/ChecklistList';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  groups: GroupResponse[];
  actions: ActionResponse[];
  days?: DayResponse[];
  cycle?: CycleResponse | null;
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
  kind: DayKind | null;
  actions: ActionResponse[];
};

function dayKindLabel(
  kind: DayKind,
  t: (key: string) => string,
): string {
  switch (kind) {
    case 'train':
      return t('dayKind.train');
    case 'rest':
      return t('dayKind.rest');
    case 'cook_session':
      return t('dayKind.cook_session');
    case 'other':
      return t('dayKind.other');
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }
}

function buildDaySections(
  days: DayResponse[],
  actions: ActionResponse[],
  t: (key: string, opts?: Record<string, unknown>) => string,
): Section[] {
  const sortedDays = [...days].sort((a, b) => a.day_index - b.day_index);
  const sortedActions = [...actions].sort((a, b) => {
    const dayA = a.day_offset ?? 10 ** 9;
    const dayB = b.day_offset ?? 10 ** 9;
    if (dayA !== dayB) return dayA - dayB;
    return a.sort - b.sort;
  });
  const byDay = new Map<number, ActionResponse[]>();
  const unscheduled: ActionResponse[] = [];

  for (const action of sortedActions) {
    if (action.day_offset == null) {
      unscheduled.push(action);
      continue;
    }
    const list = byDay.get(action.day_offset) ?? [];
    list.push(action);
    byDay.set(action.day_offset, list);
  }

  const sections: Section[] = sortedDays.map((day) => {
    const kindLabel = dayKindLabel(day.kind, t);
    const dayTitle = t('path.dayHeader', {
      n: day.day_index + 1,
      kind: kindLabel,
    });
    const subtitle = day.title
      ? day.summary
        ? `${day.title} — ${day.summary}`
        : day.title
      : day.summary ?? null;
    return {
      key: `day-${day.day_index}`,
      title: dayTitle,
      description: subtitle,
      kind: day.kind,
      actions: byDay.get(day.day_index) ?? [],
    };
  });

  if (unscheduled.length > 0) {
    sections.push({
      key: '_unscheduled',
      title: null,
      description: null,
      kind: null,
      actions: unscheduled,
    });
  }

  return sections;
}

function buildGroupSections(
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
      kind: null,
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
      kind: null,
      actions: list,
    });
  }

  if (ungrouped.length > 0) {
    sections.push({
      key: '_ungrouped',
      title: null,
      description: null,
      kind: null,
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
  days,
  cycle,
  compact = false,
  expandable = false,
  checklistDisabled,
  onToggleChecklist,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [expanded, setExpanded] = useState(!compact);
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});
  const useDays = Boolean(days && days.length > 0);
  const sections = useDays
    ? buildDaySections(days ?? [], actions, t)
    : buildGroupSections(groups, actions);
  const showDetail = !compact || expanded;

  if (actions.length === 0) {
    return null;
  }

  const toggleOpen = (id: string) => {
    setOpenIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <View style={styles.root}>
      {cycle && showDetail ? (
        <Text style={[styles.cycleLabel, { color: colors.textMuted }]}>
          {t('path.cyclePlan', { days: cycle.horizon_days })}
        </Text>
      ) : null}

      {!showDetail ? (
        <View style={styles.preview}>
          {(useDays ? days ?? [] : [])
            .slice()
            .sort((a, b) => a.day_index - b.day_index)
            .slice(0, 4)
            .map((day) => (
              <Text
                key={day.day_index}
                style={[styles.previewRow, { color: colors.text }]}
                numberOfLines={1}
              >
                {t('path.dayHeader', {
                  n: day.day_index + 1,
                  kind: dayKindLabel(day.kind, t),
                })}
                {day.title ? ` · ${day.title}` : ''}
              </Text>
            ))}
          {!useDays
            ? actions
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
                ))
            : null}
          {(useDays ? (days?.length ?? 0) > 4 : actions.length > 3) ? (
            <Text style={[styles.more, { color: colors.textMuted }]}>…</Text>
          ) : null}
        </View>
      ) : (
        sections.map((section) => (
          <View
            key={section.key}
            style={[
              styles.section,
              section.kind === 'rest'
                ? {
                    backgroundColor: colors.surface,
                    borderRadius: radii.md,
                    padding: spacing.md,
                    borderWidth: 1,
                    borderColor: colors.border,
                  }
                : null,
            ]}
          >
            {section.title ? (
              <Text
                style={[
                  styles.groupTitle,
                  {
                    color:
                      section.kind === 'rest'
                        ? colors.textSecondary
                        : colors.textMuted,
                  },
                ]}
              >
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
            {section.actions.length === 0 && section.kind === 'rest' ? (
              <Text style={[styles.meta, { color: colors.textSecondary }]}>
                {t('path.restEmpty')}
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
              const prev = section.actions[index - 1];
              const showGroup =
                Boolean(action.group_title) &&
                action.group_title !== prev?.group_title;

              return (
                <View key={action.id}>
                  {showGroup ? (
                    <Text
                      style={[
                        styles.innerGroup,
                        { color: colors.textMuted },
                      ]}
                    >
                      {action.group_title}
                    </Text>
                  ) : null}
                  <View
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
                          style={[
                            styles.stepTitle,
                            { color: colors.text, flex: 1 },
                          ]}
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
                            style={[
                              styles.detail,
                              { color: colors.textSecondary },
                            ]}
                          >
                            {action.why}
                          </Text>
                        ) : null}
                        {action.detail ? (
                          <Text
                            style={[
                              styles.detail,
                              { color: colors.textSecondary },
                            ]}
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
  cycleLabel: {
    ...typography.label,
    marginBottom: spacing.xs,
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
  innerGroup: {
    ...typography.caption,
    textTransform: 'uppercase',
    marginTop: spacing.xs,
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
