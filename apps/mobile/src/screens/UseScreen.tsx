import React, { useEffect, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';

import { useDesk } from '@/store/DeskContext';
import { colors, radii, spacing, typography } from '@/theme';
import type { RootStackParamList } from '@/navigation/types';

type Props = NativeStackScreenProps<RootStackParamList, 'Use'>;

function quietDate(iso: string | null | undefined): string {
  const date = iso ? new Date(iso) : new Date();
  return date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}

export function UseScreen({ navigation, route }: Props) {
  const insets = useSafeAreaInsets();
  const desk = useDesk();
  const widget = desk.widgets.find((item) => item.id === route.params.widgetId);
  const instance = desk.instances.find((item) => item.id === widget?.instance_id);
  const cue = widget ? desk.cueFor(widget.subject_id) : undefined;

  const [cueDraft, setCueDraft] = useState(cue?.text ?? '');
  const [goalDraft, setGoalDraft] = useState(String(widget?.payload.target ?? ''));
  const openedDone = useRef(widget?.status === 'done');
  const startedRef = useRef(false);

  useEffect(() => {
    if (!widget || startedRef.current) return;
    startedRef.current = true;
    if (widget.status !== 'done') {
      desk.startInstance(widget.id);
    }
    desk.markCueSurfaced(widget.id, 'use');
  }, [desk, widget]);

  useEffect(() => {
    if (cue) setCueDraft(cue.text);
  }, [cue]);

  useEffect(() => {
    if (!openedDone.current && widget?.status === 'done') {
      navigation.goBack();
    }
  }, [navigation, widget?.status]);

  if (!widget || widget.type !== 'counter') {
    return (
      <View style={[styles.root, { paddingTop: insets.top }]}>
        <Pressable onPress={() => navigation.goBack()} style={styles.back}>
          <Text style={styles.backText}>Назад</Text>
        </Pressable>
        <Text style={styles.missing}>Этого счётчика уже нет на крышке.</Text>
      </View>
    );
  }

  const count = widget.payload.count ?? 0;
  const target = widget.payload.target ?? 0;

  const commitCue = () => {
    if (cue && cueDraft.trim() && cueDraft.trim() !== cue.text) {
      desk.editCueText(cue.id, cueDraft.trim());
    }
  };

  const commitGoal = () => {
    const goal = Number.parseInt(goalDraft, 10);
    if (Number.isFinite(goal) && goal >= 1 && goal !== target) {
      desk.editTarget(widget.id, goal);
    } else {
      setGoalDraft(String(target));
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.root, { paddingTop: insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.bar}>
        <Pressable onPress={() => navigation.goBack()} hitSlop={12} style={styles.back}>
          <Text style={styles.backText}>Назад</Text>
        </Pressable>
        <Text style={styles.date}>{quietDate(instance?.when)}</Text>
        <View style={styles.back} />
      </View>

      <Text style={styles.title}>{widget.title}</Text>

      <View style={styles.numberBlock}>
        <Text style={styles.number}>{count}</Text>
        <View style={styles.goalRow}>
          <Text style={styles.goalSlash}>/</Text>
          <TextInput
            value={goalDraft}
            onChangeText={setGoalDraft}
            onEndEditing={commitGoal}
            keyboardType="number-pad"
            style={styles.goalInput}
            accessibilityLabel="цель"
          />
        </View>
      </View>

      <TextInput
        value={cueDraft}
        onChangeText={setCueDraft}
        onEndEditing={commitCue}
        multiline
        style={styles.cue}
        accessibilityLabel="подсказка"
      />
      <Text style={styles.editHint}>можно править текст и цель</Text>

      <View style={styles.buttons}>
        <Pressable
          onPress={() => desk.tickCounter(widget.id, -1)}
          style={styles.step}
          accessibilityLabel="минус"
        >
          <Text style={styles.stepText}>−</Text>
        </Pressable>
        <Pressable
          onPress={() => desk.tickCounter(widget.id, 1)}
          style={[styles.step, styles.stepPlus]}
          accessibilityLabel="плюс"
        >
          <Text style={[styles.stepText, styles.stepPlusText]}>+</Text>
        </Pressable>
      </View>

      <Pressable
        onPress={() => desk.completeCounter(widget.id)}
        style={[styles.done, { marginBottom: insets.bottom + spacing.md }]}
      >
        <Text style={styles.doneText}>Готово</Text>
      </Pressable>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: colors.background,
    paddingHorizontal: spacing.lg,
  },
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: spacing.sm,
  },
  back: {
    minWidth: 64,
  },
  backText: {
    ...typography.subtitle,
    color: colors.primary,
  },
  date: {
    ...typography.caption,
    color: colors.textMuted,
  },
  title: {
    ...typography.title,
    color: colors.text,
    marginTop: spacing.sm,
  },
  numberBlock: {
    alignItems: 'center',
    marginTop: spacing.xl,
  },
  number: {
    ...typography.hero,
    color: colors.text,
  },
  goalRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  goalSlash: {
    ...typography.subtitle,
    color: colors.textMuted,
    marginRight: spacing.xs,
  },
  goalInput: {
    ...typography.subtitle,
    color: colors.textSecondary,
    minWidth: 48,
    paddingVertical: spacing.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
    textAlign: 'center',
  },
  cue: {
    marginTop: spacing.xl,
    ...typography.title,
    color: colors.primary,
    lineHeight: 30,
    textAlign: 'center',
    paddingHorizontal: spacing.sm,
  },
  editHint: {
    ...typography.caption,
    color: colors.textMuted,
    textAlign: 'center',
    marginTop: spacing.xs,
  },
  buttons: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.lg,
    marginTop: spacing.xl,
  },
  step: {
    width: 72,
    height: 72,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepPlus: {
    borderColor: colors.primary,
    backgroundColor: colors.primary,
  },
  stepText: {
    fontSize: 36,
    fontWeight: '600',
    color: colors.text,
    marginTop: -2,
  },
  stepPlusText: {
    color: colors.white,
  },
  done: {
    marginTop: 'auto',
    backgroundColor: colors.primary,
    borderRadius: radii.lg,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  doneText: {
    ...typography.subtitle,
    color: colors.white,
  },
  missing: {
    ...typography.body,
    color: colors.textSecondary,
    marginTop: spacing.lg,
  },
});
