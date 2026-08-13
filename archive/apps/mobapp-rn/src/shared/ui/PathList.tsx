import React, { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type {
  ActionResponse,
  ChecklistItemResponse,
  CycleResponse,
  DayKind,
  DayResponse,
  GroupResponse,
} from '@/api/types';
import {
  CounterControl,
  IntervalPlayer,
  StepperPlayer,
  TimelineProgress,
  TimerStack,
} from '@/shared/ui/ActionPlugins';
import { ChecklistList } from '@/shared/ui/ChecklistList';
import { capitalizeLabel, dayKindLabel } from '@/shared/ui/dayLabels';
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
  /** When true, timers/counters can run (live). Default false = preview. */
  pluginsInteractive?: boolean;
  /**
   * Manual entry for a specific action’s Block tools (path-state action id /
   * ActionResponse.key). Create plan card + Active Session.
   */
  onEditAction?: (actionKey: string) => void;
  onToggleChecklist?: (
    item: ChecklistItemResponse,
    nextDone: boolean,
  ) => void;
  onCounterChange?: (actionId: string, nextCurrent: number) => void;
  onStepperBeatCounterChange?: (
    actionId: string,
    beatId: string,
    nextCurrent: number,
  ) => void;
  onCompleteTimer?: (actionId: string, timerId: string) => void;
};

type Section = {
  key: string;
  title: string | null;
  description: string | null;
  kind: DayKind | null;
  actions: ActionResponse[];
};

function pluginHintLabel(
  hint: string,
  t: (key: string) => string,
): string {
  switch (hint) {
    case 'timers':
      return t('plugins.hintTimers');
    case 'timeline':
      return t('plugins.hintTimeline');
    case 'interval':
      return t('plugins.hintInterval');
    case 'counter':
      return t('plugins.hintCounter');
    case 'stepper':
      return t('plugins.hintStepper');
    default:
      return hint;
  }
}

function actionHasLivePlugins(action: ActionResponse): boolean {
  return (
    (action.timers?.length ?? 0) > 0 ||
    Boolean(action.counter) ||
    Boolean(action.timeline) ||
    Boolean(action.interval_plan) ||
    Boolean(action.stepper)
  );
}

function visiblePluginHints(action: ActionResponse): string[] {
  if (actionHasLivePlugins(action)) return [];
  return (action.plugin_hints ?? []).filter(Boolean);
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
    const kindLabel = capitalizeLabel(dayKindLabel(day.kind, t));
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
  action: ActionResponse,
  t: (key: string) => string,
): string | null {
  switch (action.status) {
    case 'done':
      return t('path.statusDone');
    case 'skipped':
      return t('path.statusSkipped');
    case 'pending':
      return action.day_locked ? t('path.statusLocked') : null;
    default: {
      const _exhaustive: never = action.status;
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
  pluginsInteractive = false,
  onEditAction,
  onToggleChecklist,
  onCounterChange,
  onStepperBeatCounterChange,
  onCompleteTimer,
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
  // Multi-day maps: Day is the only section header. Single-day (e.g. cook
  // session) may keep subtle in-day group captions for shop/cook clusters.
  const showInnerGroups = useDays && (days?.length ?? 0) === 1;

  if (actions.length === 0) {
    return null;
  }

  const hasEditableBlock = (action: ActionResponse): boolean =>
    action.checklist_items.length > 0 ||
    Boolean(action.counter) ||
    Boolean(action.stepper);

  const isActionOpen = (action: ActionResponse): boolean => {
    if (!expandable) return true;
    if (openIds[action.id] !== undefined) return Boolean(openIds[action.id]);
    // With Block Edit, open tool-bearing steps by default so Edit+pencil is
    // visible without hunting «expand» (#12).
    return onEditAction != null && hasEditableBlock(action);
  };

  const toggleOpen = (id: string) => {
    setOpenIds((prev) => {
      const action = actions.find((a) => a.id === id);
      const currentlyOpen =
        prev[id] !== undefined
          ? Boolean(prev[id])
          : onEditAction != null &&
            action != null &&
            hasEditableBlock(action);
      return { ...prev, [id]: !currentlyOpen };
    });
  };

  const editKeyFor = (action: ActionResponse): string | null => {
    const key = action.key?.trim();
    return key || null;
  };

  const editHandler = (action: ActionResponse): (() => void) | undefined => {
    if (!onEditAction) return undefined;
    const key = editKeyFor(action);
    if (!key) return undefined;
    return () => onEditAction(key);
  };

  return (
    <View style={styles.root}>
      {cycle && showDetail ? (
        <Text style={[styles.cycleLabel, { color: colors.textSecondary }]}>
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
                  kind: capitalizeLabel(dayKindLabel(day.kind, t)),
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
        sections.map((section) => {
          const isDaySection = useDays && section.kind != null;
          const isRestDay = section.kind === 'rest';
          const isDayLocked =
            isDaySection &&
            section.actions.length > 0 &&
            section.actions.every(
              (a) => a.day_locked && a.status === 'pending',
            );
          return (
            <View
              key={section.key}
              style={[
                styles.section,
                isRestDay
                  ? {
                      borderLeftWidth: 3,
                      borderLeftColor: colors.border,
                      paddingLeft: spacing.sm,
                      opacity: 0.92,
                    }
                  : null,
              ]}
            >
              {section.title ? (
                <View style={styles.dayTitleRow}>
                  <Text
                    style={[
                      isDaySection ? styles.dayTitle : styles.groupTitle,
                      {
                        color: isDaySection
                          ? isRestDay
                            ? colors.textSecondary
                            : colors.text
                          : colors.textMuted,
                      },
                    ]}
                  >
                    {section.title}
                  </Text>
                  {isDayLocked ? (
                    <View
                      style={[
                        styles.hintChip,
                        {
                          borderColor: colors.border,
                          backgroundColor: colors.surface,
                        },
                      ]}
                    >
                      <Text
                        style={[
                          styles.hintText,
                          { color: colors.textSecondary },
                        ]}
                      >
                        {t('path.statusLocked')}
                      </Text>
                    </View>
                  ) : null}
                </View>
              ) : null}
              {section.description ? (
                <Text
                  style={[
                    styles.groupDescription,
                    { color: colors.textSecondary },
                  ]}
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
                const status = statusLabel(action, t);
                const isLocked = Boolean(action.day_locked);
                const isOpen = isActionOpen(action);
                const canExpand =
                  expandable &&
                  Boolean(
                    action.detail ||
                      action.why ||
                      action.checklist_items.length > 0 ||
                      (action.timers?.length ?? 0) > 0 ||
                      action.counter ||
                      action.timeline ||
                      action.interval_plan ||
                      action.stepper ||
                      visiblePluginHints(action).length > 0,
                  );
                const prev = section.actions[index - 1];
                const showGroup =
                  showInnerGroups &&
                  Boolean(action.group_title) &&
                  action.group_title !== prev?.group_title;

                return (
                  <View key={action.id}>
                    {showGroup ? (
                      <Text
                        style={[
                          styles.innerGroup,
                          { color: colors.textSecondary },
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
                          opacity:
                            action.status === 'pending' && !isLocked
                              ? 1
                              : 0.72,
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
                            style={[
                              styles.meta,
                              { color: colors.textSecondary },
                            ]}
                          >
                            {t('common.minutes', {
                              count: action.estimate_min,
                            })}
                          </Text>
                        ) : null}
                        {visiblePluginHints(action).length > 0 ? (
                          <View style={styles.hintRow}>
                            {visiblePluginHints(action).map((hint) => (
                              <View
                                key={hint}
                                style={[
                                  styles.hintChip,
                                  {
                                    borderColor: colors.border,
                                    backgroundColor: colors.surface,
                                  },
                                ]}
                              >
                                <Text
                                  style={[
                                    styles.hintText,
                                    { color: colors.textSecondary },
                                  ]}
                                >
                                  {pluginHintLabel(hint, t)}
                                </Text>
                              </View>
                            ))}
                          </View>
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
                                checklistDisabled ||
                                action.status !== 'pending' ||
                                isLocked
                              }
                              onEdit={editHandler(action)}
                              onToggle={
                                onToggleChecklist &&
                                action.status === 'pending' &&
                                !isLocked
                                  ? onToggleChecklist
                                  : undefined
                              }
                            />
                          ) : null}
                          {(action.timers?.length ?? 0) > 0 ? (
                            <TimerStack
                              timers={action.timers ?? []}
                              interactive={
                                pluginsInteractive &&
                                action.status === 'pending' &&
                                !isLocked
                              }
                              disabled={checklistDisabled}
                              onCompleteTimer={
                                onCompleteTimer
                                  ? (timerId) =>
                                      onCompleteTimer(action.id, timerId)
                                  : undefined
                              }
                            />
                          ) : null}
                          {action.timeline ? (
                            <TimelineProgress
                              timeline={action.timeline}
                              interactive={
                                pluginsInteractive &&
                                action.status === 'pending' &&
                                !isLocked
                              }
                              disabled={checklistDisabled}
                            />
                          ) : null}
                          {action.interval_plan ? (
                            <IntervalPlayer
                              plan={action.interval_plan}
                              interactive={
                                pluginsInteractive &&
                                action.status === 'pending' &&
                                !isLocked
                              }
                              disabled={checklistDisabled}
                            />
                          ) : null}
                          {action.counter ? (
                            <CounterControl
                              counter={action.counter}
                              interactive={
                                pluginsInteractive &&
                                action.status === 'pending' &&
                                !isLocked
                              }
                              disabled={checklistDisabled}
                              onEdit={editHandler(action)}
                              onChange={
                                onCounterChange
                                  ? (next) =>
                                      onCounterChange(action.id, next)
                                  : undefined
                              }
                            />
                          ) : null}
                          {action.stepper ? (
                            <StepperPlayer
                              stepper={action.stepper}
                              // Preview on Guide: compact strip — no Session
                              // minHeight:300 stage void inside PathList.
                              compact={!pluginsInteractive}
                              interactive={
                                pluginsInteractive &&
                                action.status === 'pending' &&
                                !isLocked
                              }
                              disabled={checklistDisabled}
                              onEdit={editHandler(action)}
                              onBeatCounterChange={
                                onStepperBeatCounterChange
                                  ? (beatId, next) =>
                                      onStepperBeatCounterChange(
                                        action.id,
                                        beatId,
                                        next,
                                      )
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
          );
        })
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
    ...typography.caption,
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
  dayTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  dayTitle: {
    ...typography.subtitle,
    fontWeight: '700',
  },
  groupTitle: {
    ...typography.label,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  innerGroup: {
    ...typography.caption,
    marginTop: spacing.xs,
    marginBottom: 2,
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
    ...typography.body,
    fontWeight: '600',
  },
  status: {
    ...typography.caption,
  },
  hintRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.xs,
    marginTop: 2,
  },
  hintChip: {
    borderWidth: 1,
    borderRadius: radii.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  hintText: {
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
