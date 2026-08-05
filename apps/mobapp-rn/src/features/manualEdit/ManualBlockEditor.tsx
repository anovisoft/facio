import React, { useCallback, useState } from 'react';
import {
  Keyboard,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import type { AnimatedRef } from 'react-native-reanimated';
import Animated from 'react-native-reanimated';
import Sortable, {
  type SortableFlexDragEndCallback,
} from 'react-native-sortables';

import {
  newChecklistItemId,
  type EditableActionTools,
  type PathChecklistItemJson,
  type PathCounterJson,
  type PathStepperBeatJson,
} from '@/features/manualEdit/pathStateTools';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const CHECKLIST_ROW_BODY = 44;

type Props = {
  actions: EditableActionTools[];
  onChange: (next: EditableActionTools[]) => void;
  disabled?: boolean;
  /** Parent Animated.ScrollView ref — enables auto-scroll while reordering. */
  scrollableRef?: AnimatedRef<Animated.ScrollView>;
};

function updateAction(
  list: EditableActionTools[],
  actionId: string,
  patch: Partial<EditableActionTools>,
): EditableActionTools[] {
  return list.map((a) => (a.actionId === actionId ? { ...a, ...patch } : a));
}

/**
 * Shared Manual editor for closed UI Block tool fields (Create + Active).
 * Checklist / stepper / counter are first-class; other scalars when present.
 */
export function ManualBlockEditor({
  actions,
  onChange,
  disabled,
  scrollableRef,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  if (actions.length === 0) {
    return (
      <Text style={[styles.empty, { color: colors.textSecondary }]}>
        {t('manualEdit.emptyTools')}
      </Text>
    );
  }

  return (
    <View style={styles.root}>
      {actions.map((action) => (
        <View
          key={action.actionId}
          style={[
            styles.actionCard,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          <Text style={[styles.actionTitle, { color: colors.text }]}>
            {action.title}
          </Text>

          {action.hintsOnly ? (
            <Text style={[styles.hintNote, { color: colors.textSecondary }]}>
              {t('manualEdit.hintsOnly', {
                tools: action.pluginHints.join(', '),
              })}
            </Text>
          ) : null}

          {action.checklistItems.length > 0 ? (
            <ChecklistEditor
              items={action.checklistItems}
              disabled={disabled}
              scrollableRef={scrollableRef}
              onChange={(checklistItems) =>
                onChange(
                  updateAction(actions, action.actionId, { checklistItems }),
                )
              }
            />
          ) : null}

          {action.checklistItems.length === 0 &&
          !action.hintsOnly &&
          !action.stepper &&
          !action.counter &&
          action.timers.length === 0 &&
          !action.timeline &&
          !action.intervalPlan ? (
            <Pressable
              disabled={disabled}
              onPress={() =>
                onChange(
                  updateAction(actions, action.actionId, {
                    checklistItems: [
                      {
                        id: newChecklistItemId(),
                        title: '',
                        done: false,
                        sort: 0,
                      },
                    ],
                  }),
                )
              }
              hitSlop={8}
            >
              <Text style={[styles.link, { color: colors.primary }]}>
                {t('manualEdit.addChecklist')}
              </Text>
            </Pressable>
          ) : null}

          {action.counter ? (
            <CounterEditor
              counter={action.counter}
              disabled={disabled}
              onChange={(counter) =>
                onChange(updateAction(actions, action.actionId, { counter }))
              }
            />
          ) : null}

          {action.stepper ? (
            <StepperEditor
              beats={action.stepper.beats}
              disabled={disabled}
              onChange={(beats) =>
                onChange(
                  updateAction(actions, action.actionId, {
                    stepper: { beats },
                  }),
                )
              }
            />
          ) : null}

          {action.timers.map((timer, index) => (
            <View key={timer.id ?? `t${index}`} style={styles.fieldBlock}>
              <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
                {t('manualEdit.timer')}
              </Text>
              <TextInput
                value={timer.title}
                editable={!disabled}
                onChangeText={(title) => {
                  const timers = action.timers.map((tm, i) =>
                    i === index ? { ...tm, title } : tm,
                  );
                  onChange(updateAction(actions, action.actionId, { timers }));
                }}
                placeholder={t('manualEdit.labelPlaceholder')}
                placeholderTextColor={colors.textMuted}
                style={[
                  styles.input,
                  {
                    color: colors.text,
                    borderColor: colors.border,
                    backgroundColor: colors.background,
                  },
                ]}
              />
              <LabeledNumber
                label={t('manualEdit.durationSec')}
                value={timer.duration_sec}
                disabled={disabled}
                onChange={(duration_sec) => {
                  const timers = action.timers.map((tm, i) =>
                    i === index ? { ...tm, duration_sec } : tm,
                  );
                  onChange(updateAction(actions, action.actionId, { timers }));
                }}
              />
            </View>
          ))}

          {action.timeline ? (
            <View style={styles.fieldBlock}>
              <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
                {t('manualEdit.timeline')}
              </Text>
              <LabeledNumber
                label={t('manualEdit.durationSec')}
                value={action.timeline.duration_sec}
                disabled={disabled}
                onChange={(duration_sec) =>
                  onChange(
                    updateAction(actions, action.actionId, {
                      timeline: { ...action.timeline!, duration_sec },
                    }),
                  )
                }
              />
              <Text style={[styles.hintNote, { color: colors.textSecondary }]}>
                {t('manualEdit.markersNotEditable')}
              </Text>
            </View>
          ) : null}

          {action.intervalPlan ? (
            <View style={styles.fieldBlock}>
              <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
                {t('manualEdit.interval')}
              </Text>
              {action.intervalPlan.segments.map((seg, index) => (
                <View key={`seg-${index}`} style={styles.row}>
                  <TextInput
                    value={seg.title}
                    editable={!disabled}
                    onChangeText={(title) => {
                      const segments = action.intervalPlan!.segments.map(
                        (s, i) => (i === index ? { ...s, title } : s),
                      );
                      onChange(
                        updateAction(actions, action.actionId, {
                          intervalPlan: { segments },
                        }),
                      );
                    }}
                    style={[
                      styles.input,
                      styles.flex,
                      {
                        color: colors.text,
                        borderColor: colors.border,
                        backgroundColor: colors.background,
                      },
                    ]}
                  />
                  <LabeledNumber
                    label={t('manualEdit.sec')}
                    value={seg.sec}
                    disabled={disabled}
                    compact
                    onChange={(sec) => {
                      const segments = action.intervalPlan!.segments.map(
                        (s, i) => (i === index ? { ...s, sec } : s),
                      );
                      onChange(
                        updateAction(actions, action.actionId, {
                          intervalPlan: { segments },
                        }),
                      );
                    }}
                  />
                </View>
              ))}
            </View>
          ) : null}
        </View>
      ))}
    </View>
  );
}

function ChecklistEditor({
  items,
  onChange,
  disabled,
  scrollableRef,
}: {
  items: PathChecklistItemJson[];
  onChange: (items: PathChecklistItemJson[]) => void;
  disabled?: boolean;
  scrollableRef?: AnimatedRef<Animated.ScrollView>;
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  /** Sortable.Flex sizes to content — pin row width so inputs share one column. */
  const [rowWidth, setRowWidth] = useState<number | undefined>();

  const onDragStart = useCallback(() => {
    Keyboard.dismiss();
  }, []);

  const onDragEnd = useCallback<SortableFlexDragEndCallback>(
    ({ order }) => {
      const next = order(items);
      if (next === items) return;
      onChange(next.map((it, i) => ({ ...it, sort: i })));
    },
    [items, onChange],
  );

  return (
    <View
      style={styles.checklistBlock}
      onLayout={(e) => {
        const w = e.nativeEvent.layout.width;
        setRowWidth((prev) => (prev === w ? prev : w));
      }}
    >
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('manualEdit.checklist')}
      </Text>
      <Sortable.Flex
        flexDirection="column"
        flexWrap="nowrap"
        alignItems="flex-start"
        width="fill"
        gap={spacing.sm}
        customHandle
        sortEnabled={!disabled && items.length > 1}
        scrollableRef={scrollableRef}
        autoScrollEnabled={scrollableRef != null}
        dragActivationDelay={0}
        activeItemScale={1.02}
        activeItemShadowOpacity={0.12}
        inactiveItemOpacity={1}
        inactiveItemScale={1}
        showDropIndicator={false}
        hapticsEnabled
        overflow="visible"
        onDragStart={onDragStart}
        onDragEnd={onDragEnd}
      >
        {items.map((item, index) => {
          const rowId = item.id ?? `c${index}`;
          return (
            <ChecklistRow
              key={rowId}
              item={item}
              disabled={disabled}
              rowWidth={rowWidth}
              onChangeTitle={(title) => {
                const next = items.map((it, i) =>
                  i === index ? { ...it, title } : it,
                );
                onChange(next);
              }}
              onRemove={() => onChange(items.filter((_, i) => i !== index))}
            />
          );
        })}
      </Sortable.Flex>
      <Pressable
        disabled={disabled}
        onPress={() =>
          onChange([
            ...items,
            {
              id: newChecklistItemId(),
              title: '',
              done: false,
              sort: items.length,
            },
          ])
        }
        hitSlop={8}
        style={styles.addItemBtn}
      >
        <Text style={[styles.link, { color: colors.primary }]}>
          {t('manualEdit.addItem')}
        </Text>
      </Pressable>
    </View>
  );
}

function ChecklistRow({
  item,
  disabled,
  rowWidth,
  onChangeTitle,
  onRemove,
}: {
  item: PathChecklistItemJson;
  disabled?: boolean;
  rowWidth?: number;
  onChangeTitle: (title: string) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  return (
    <View style={[styles.checklistRow, rowWidth != null ? { width: rowWidth } : null]}>
      <Sortable.Handle mode={disabled ? 'non-draggable' : 'draggable'}>
        <View
          style={styles.dragHandle}
          accessibilityRole="adjustable"
          accessibilityLabel={t('manualEdit.reorderItem')}
        >
          <Ionicons name="reorder-three" size={22} color={colors.textMuted} />
        </View>
      </Sortable.Handle>

      <TextInput
        value={item.title}
        editable={!disabled}
        onChangeText={onChangeTitle}
        placeholder={t('manualEdit.itemPlaceholder')}
        placeholderTextColor={colors.textMuted}
        textAlignVertical="center"
        nativeID={item.id ?? undefined}
        style={[
          styles.checklistInput,
          styles.flex,
          {
            color: colors.text,
            borderColor: colors.border,
            backgroundColor: colors.background,
          },
        ]}
      />

      <Pressable
        disabled={disabled}
        onPress={onRemove}
        hitSlop={10}
        accessibilityRole="button"
        accessibilityLabel={t('manualEdit.removeItem')}
        style={styles.deleteHit}
      >
        <Ionicons name="close" size={20} color={colors.error} />
      </Pressable>
    </View>
  );
}

function CounterEditor({
  counter,
  onChange,
  disabled,
}: {
  counter: PathCounterJson;
  onChange: (c: PathCounterJson) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  return (
    <View style={styles.fieldBlock}>
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('manualEdit.counter')}
      </Text>
      <TextInput
        value={counter.label ?? ''}
        editable={!disabled}
        onChangeText={(label) => onChange({ ...counter, label })}
        placeholder={t('manualEdit.labelPlaceholder')}
        placeholderTextColor={colors.textMuted}
        style={[
          styles.input,
          {
            color: colors.text,
            borderColor: colors.border,
            backgroundColor: colors.background,
          },
        ]}
      />
      <LabeledNumber
        label={t('manualEdit.target')}
        value={counter.target}
        disabled={disabled}
        onChange={(target) => onChange({ ...counter, target })}
      />
    </View>
  );
}

function StepperEditor({
  beats,
  onChange,
  disabled,
}: {
  beats: PathStepperBeatJson[];
  onChange: (beats: PathStepperBeatJson[]) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  return (
    <View style={styles.fieldBlock}>
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('manualEdit.stepper')}
      </Text>
      {beats.map((beat, index) => (
        <View
          key={beat.id ?? `b${index}`}
          style={[styles.beatCard, { borderColor: colors.border }]}
        >
          <Text style={[styles.beatKind, { color: colors.textMuted }]}>
            {beat.kind}
          </Text>
          <TextInput
            value={beat.title}
            editable={!disabled}
            onChangeText={(title) => {
              const next = beats.map((b, i) =>
                i === index ? { ...b, title } : b,
              );
              onChange(next);
            }}
            placeholder={t('manualEdit.labelPlaceholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.input,
              {
                color: colors.text,
                borderColor: colors.border,
                backgroundColor: colors.background,
              },
            ]}
          />
          {beat.kind === 'rest' ? (
            <LabeledNumber
              label={t('manualEdit.durationSec')}
              value={beat.duration_sec ?? 60}
              disabled={disabled}
              onChange={(duration_sec) => {
                const next = beats.map((b, i) =>
                  i === index ? { ...b, duration_sec } : b,
                );
                onChange(next);
              }}
            />
          ) : (
            <>
              <TextInput
                value={beat.counter?.label ?? ''}
                editable={!disabled}
                onChangeText={(label) => {
                  const next = beats.map((b, i) =>
                    i === index
                      ? {
                          ...b,
                          counter: {
                            label,
                            target: b.counter?.target ?? 1,
                            current: b.counter?.current ?? 0,
                            step: b.counter?.step ?? 1,
                          },
                        }
                      : b,
                  );
                  onChange(next);
                }}
                placeholder={t('manualEdit.labelPlaceholder')}
                placeholderTextColor={colors.textMuted}
                style={[
                  styles.input,
                  {
                    color: colors.text,
                    borderColor: colors.border,
                    backgroundColor: colors.background,
                  },
                ]}
              />
              <LabeledNumber
                label={t('manualEdit.target')}
                value={beat.counter?.target ?? 1}
                disabled={disabled}
                onChange={(target) => {
                  const next = beats.map((b, i) =>
                    i === index
                      ? {
                          ...b,
                          counter: {
                            label: b.counter?.label ?? null,
                            target,
                            current: b.counter?.current ?? 0,
                            step: b.counter?.step ?? 1,
                          },
                        }
                      : b,
                  );
                  onChange(next);
                }}
              />
            </>
          )}
        </View>
      ))}
    </View>
  );
}

function LabeledNumber({
  label,
  value,
  onChange,
  disabled,
  compact,
}: {
  label: string;
  value: number;
  onChange: (n: number) => void;
  disabled?: boolean;
  compact?: boolean;
}) {
  const { colors } = useTheme();
  return (
    <View style={compact ? styles.numCompact : styles.numRow}>
      <Text style={[styles.numLabel, { color: colors.textSecondary }]}>
        {label}
      </Text>
      <TextInput
        value={String(value)}
        editable={!disabled}
        keyboardType="number-pad"
        onChangeText={(text) => {
          const n = parseInt(text.replace(/[^0-9]/g, ''), 10);
          onChange(Number.isFinite(n) ? n : 0);
        }}
        style={[
          styles.input,
          styles.numInput,
          {
            color: colors.text,
            borderColor: colors.border,
            backgroundColor: colors.background,
          },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.md,
    alignSelf: 'stretch',
  },
  empty: {
    ...typography.body,
  },
  actionCard: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.sm,
  },
  actionTitle: {
    ...typography.subtitle,
    fontWeight: '700',
  },
  fieldBlock: {
    gap: spacing.xs,
    marginTop: spacing.xs,
  },
  checklistBlock: {
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  sectionLabel: {
    ...typography.label,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  input: {
    ...typography.body,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.md,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
    minHeight: 44,
  },
  checklistInput: {
    fontSize: typography.body.fontSize,
    fontWeight: typography.body.fontWeight,
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.md,
    height: CHECKLIST_ROW_BODY,
    paddingHorizontal: spacing.sm,
    paddingTop: 0,
    paddingBottom: 0,
    margin: 0,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  checklistRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  flex: {
    flex: 1,
    minWidth: 0,
  },
  dragHandle: {
    width: CHECKLIST_ROW_BODY,
    height: CHECKLIST_ROW_BODY,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deleteHit: {
    width: CHECKLIST_ROW_BODY,
    height: CHECKLIST_ROW_BODY,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addItemBtn: {
    marginTop: spacing.sm,
    paddingVertical: spacing.sm,
    alignSelf: 'flex-start',
  },
  link: {
    ...typography.caption,
    fontWeight: '600',
  },
  hintNote: {
    ...typography.caption,
  },
  beatCard: {
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.md,
    padding: spacing.sm,
    gap: spacing.xs,
  },
  beatKind: {
    ...typography.caption,
    fontWeight: '700',
    textTransform: 'uppercase',
  },
  numRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  numCompact: {
    width: 88,
    gap: 2,
  },
  numLabel: {
    ...typography.caption,
    minWidth: 72,
  },
  numInput: {
    minWidth: 72,
    textAlign: 'center',
  },
});
