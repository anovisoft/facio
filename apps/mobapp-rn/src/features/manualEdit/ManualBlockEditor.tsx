import React, { useRef, useState } from 'react';
import {
  Animated,
  Keyboard,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';
import {
  PanGestureHandler,
  State,
  type PanGestureHandlerGestureEvent,
  type PanGestureHandlerStateChangeEvent,
} from 'react-native-gesture-handler';

import {
  newChecklistItemId,
  type EditableActionTools,
  type PathChecklistItemJson,
  type PathCounterJson,
  type PathStepperBeatJson,
} from '@/features/manualEdit/pathStateTools';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

/** Row body height + gap between rows — used for drag hover math. */
const CHECKLIST_ROW_BODY = 44;
const CHECKLIST_ROW_GAP = 8;
const CHECKLIST_ROW_STRIDE = CHECKLIST_ROW_BODY + CHECKLIST_ROW_GAP;

type Props = {
  actions: EditableActionTools[];
  onChange: (next: EditableActionTools[]) => void;
  disabled?: boolean;
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
export function ManualBlockEditor({ actions, onChange, disabled }: Props) {
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

function reorderChecklist(
  items: PathChecklistItemJson[],
  from: number,
  to: number,
): PathChecklistItemJson[] {
  if (from === to || from < 0 || to < 0 || from >= items.length || to >= items.length) {
    return items;
  }
  const next = [...items];
  const [moved] = next.splice(from, 1);
  next.splice(to, 0, moved);
  return next.map((it, i) => ({ ...it, sort: i }));
}

/**
 * While `from` is absolutely positioned, siblings stay in normal flow.
 * Insert one stride of space at `hover` via margin (no transforms).
 */
function checklistFlowGap(
  index: number,
  from: number,
  hover: number,
  itemCount: number,
): { marginTop: number; marginBottom: number } {
  const flowIndices: number[] = [];
  for (let i = 0; i < itemCount; i++) {
    if (i !== from) flowIndices.push(i);
  }
  const flowPos = flowIndices.indexOf(index);
  if (flowPos < 0) {
    return { marginTop: 0, marginBottom: CHECKLIST_ROW_GAP };
  }
  const marginTop = flowPos === hover ? CHECKLIST_ROW_STRIDE : 0;
  const trailingGap =
    hover === itemCount - 1 && flowPos === flowIndices.length - 1;
  return {
    marginTop,
    marginBottom:
      CHECKLIST_ROW_GAP + (trailingGap ? CHECKLIST_ROW_STRIDE : 0),
  };
}

type ChecklistDrag = {
  /** Stable identity — never attach chrome by index after reorder. */
  id: string;
  from: number;
  hover: number;
};

function ChecklistEditor({
  items,
  onChange,
  disabled,
}: {
  items: PathChecklistItemJson[];
  onChange: (items: PathChecklistItemJson[]) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [drag, setDrag] = useState<ChecklistDrag | null>(null);
  /** Finger offset for the absolute overlay row only. */
  const dragTy = useRef(new Animated.Value(0)).current;
  const itemsRef = useRef(items);
  itemsRef.current = items;

  const clearDragVisual = () => {
    dragTy.stopAnimation();
    dragTy.setValue(0);
    setDrag(null);
  };

  return (
    <View style={styles.checklistBlock}>
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('manualEdit.checklist')}
      </Text>
      <View
        style={[
          styles.checklistList,
          drag
            ? { minHeight: items.length * CHECKLIST_ROW_STRIDE }
            : null,
        ]}
      >
        {items.map((item, index) => {
          const rowId = item.id ?? `c${index}`;
          const isDragging = drag?.id === rowId;
          const gap =
            drag && !isDragging
              ? checklistFlowGap(index, drag.from, drag.hover, items.length)
              : { marginTop: 0, marginBottom: CHECKLIST_ROW_GAP };
          return (
            <ChecklistRow
              key={rowId}
              item={item}
              index={index}
              itemCount={items.length}
              disabled={disabled}
              listDragging={drag != null}
              dragging={isDragging}
              overlayTop={isDragging ? drag.from * CHECKLIST_ROW_STRIDE : 0}
              flowMarginTop={gap.marginTop}
              flowMarginBottom={gap.marginBottom}
              dragTy={isDragging ? dragTy : null}
              onDragStart={() => {
                Keyboard.dismiss();
                dragTy.stopAnimation();
                dragTy.setValue(0);
                setDrag({ id: rowId, from: index, hover: index });
              }}
              onDragMove={(from, translationY) => {
                dragTy.setValue(translationY);
                const count = itemsRef.current.length;
                const delta = Math.round(translationY / CHECKLIST_ROW_STRIDE);
                const hover = Math.max(0, Math.min(count - 1, from + delta));
                setDrag((prev) => {
                  if (!prev || prev.from !== from) return prev;
                  if (prev.hover === hover) return prev;
                  return { ...prev, hover };
                });
              }}
              onDragEnd={(from, to) => {
                const next = reorderChecklist(itemsRef.current, from, to);
                // Drop chrome first by id, then commit order in the same tick
                // so drag.from never paints on the post-reorder index.
                dragTy.stopAnimation();
                dragTy.setValue(0);
                setDrag(null);
                itemsRef.current = next;
                onChange(next);
              }}
              onDragCancel={clearDragVisual}
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
      </View>
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
  index,
  itemCount,
  disabled,
  listDragging,
  dragging,
  overlayTop,
  flowMarginTop,
  flowMarginBottom,
  dragTy,
  onDragStart,
  onDragMove,
  onDragEnd,
  onDragCancel,
  onChangeTitle,
  onRemove,
}: {
  item: PathChecklistItemJson;
  index: number;
  itemCount: number;
  disabled?: boolean;
  /** Any row is being dragged — blur/lock inputs so focus ring can't stick. */
  listDragging: boolean;
  dragging: boolean;
  /** Absolute top while dragging (from-index × stride). */
  overlayTop: number;
  flowMarginTop: number;
  flowMarginBottom: number;
  dragTy: Animated.Value | null;
  onDragStart: () => void;
  onDragMove: (from: number, translationY: number) => void;
  onDragEnd: (from: number, to: number) => void;
  onDragCancel: () => void;
  onChangeTitle: (title: string) => void;
  onRemove: () => void;
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const startIndexRef = useRef(index);
  const inputRef = useRef<TextInput>(null);

  const onGestureEvent = (e: PanGestureHandlerGestureEvent) => {
    onDragMove(startIndexRef.current, e.nativeEvent.translationY);
  };

  const onHandlerStateChange = (e: PanGestureHandlerStateChangeEvent) => {
    const { state, translationY } = e.nativeEvent;
    if (state === State.BEGAN) {
      startIndexRef.current = index;
      inputRef.current?.blur();
      Keyboard.dismiss();
      onDragStart();
      return;
    }
    if (state === State.ACTIVE) {
      onDragMove(startIndexRef.current, translationY);
      return;
    }
    if (
      state === State.END ||
      state === State.CANCELLED ||
      state === State.FAILED
    ) {
      if (state === State.END) {
        const delta = Math.round(translationY / CHECKLIST_ROW_STRIDE);
        const to = Math.max(
          0,
          Math.min(itemCount - 1, startIndexRef.current + delta),
        );
        onDragEnd(startIndexRef.current, to);
      } else {
        onDragCancel();
      }
    }
  };

  return (
    <Animated.View
      style={[
        styles.checklistRow,
        dragging
          ? {
              position: 'absolute',
              left: 0,
              right: 0,
              top: overlayTop,
              height: CHECKLIST_ROW_BODY,
              marginTop: 0,
              marginBottom: 0,
              transform: [{ translateY: dragTy ?? 0 }],
              zIndex: 10,
              elevation: 6,
              backgroundColor: colors.surface,
              // No border — shadow only. Border was sticking on the wrong
              // index after reorder when chrome was keyed by `from`.
              borderWidth: 0,
              borderColor: 'transparent',
              shadowOpacity: 0.14,
              shadowRadius: 8,
              shadowOffset: { width: 0, height: 3 },
              shadowColor: '#000',
            }
          : {
              position: 'relative',
              height: CHECKLIST_ROW_BODY,
              marginTop: flowMarginTop,
              marginBottom: flowMarginBottom,
              transform: [{ translateY: 0 }],
              zIndex: 0,
              elevation: 0,
              backgroundColor: 'transparent',
              borderWidth: 0,
              borderColor: 'transparent',
              shadowOpacity: 0,
              shadowRadius: 0,
              shadowOffset: { width: 0, height: 0 },
              shadowColor: 'transparent',
            },
      ]}
      pointerEvents="box-none"
    >
      <PanGestureHandler
        enabled={!disabled && itemCount > 1}
        activeOffsetY={[-6, 6]}
        failOffsetX={[-24, 24]}
        onGestureEvent={onGestureEvent}
        onHandlerStateChange={onHandlerStateChange}
      >
        <Animated.View
          style={[
            styles.dragHandle,
            {
              backgroundColor: colors.surfaceMuted,
              borderColor: colors.border,
            },
          ]}
          accessibilityRole="adjustable"
          accessibilityLabel={t('manualEdit.reorderItem')}
        >
          <Ionicons name="reorder-three" size={22} color={colors.textMuted} />
        </Animated.View>
      </PanGestureHandler>

      <TextInput
        ref={inputRef}
        value={item.title}
        editable={!disabled && !listDragging}
        onChangeText={onChangeTitle}
        placeholder={t('manualEdit.itemPlaceholder')}
        placeholderTextColor={colors.textMuted}
        textAlignVertical="center"
        // Stable identity for controlled updates after reorder.
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
        disabled={disabled || listDragging}
        onPress={onRemove}
        hitSlop={10}
        accessibilityRole="button"
        accessibilityLabel={t('manualEdit.removeItem')}
        style={[styles.deleteHit, { backgroundColor: colors.surfaceMuted }]}
      >
        <Ionicons name="close" size={20} color={colors.error} />
      </Pressable>
    </Animated.View>
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
  checklistList: {
    position: 'relative',
    // Gaps are marginBottom on rows so drag stride stays stable.
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
    borderRadius: radii.md,
    paddingHorizontal: 2,
  },
  dragHandle: {
    width: CHECKLIST_ROW_BODY,
    height: CHECKLIST_ROW_BODY,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deleteHit: {
    width: CHECKLIST_ROW_BODY,
    height: CHECKLIST_ROW_BODY,
    borderRadius: radii.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addItemBtn: {
    marginTop: spacing.sm,
    paddingVertical: spacing.sm,
    alignSelf: 'flex-start',
  },
  flex: {
    flex: 1,
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
