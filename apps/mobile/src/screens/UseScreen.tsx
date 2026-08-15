import React, { useEffect, useMemo, useRef, useState } from 'react';
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

import { WhenModal } from '@/components/WhenModal';
import { clockPartsFromWindow, formatFireClock } from '@/domain/reminder';
import type { Cue, Widget, Window } from '@/domain/types';
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
  const subject = desk.subjects.find((item) => item.id === widget?.subject_id);

  const openedDone = useRef(widget?.status === 'done');
  const surfacedRef = useRef(false);

  useEffect(() => {
    if (!widget || surfacedRef.current) return;
    surfacedRef.current = true;
    desk.markCueSurfaced(widget.id, 'use');
  }, [desk, widget]);

  useEffect(() => {
    if (!openedDone.current && widget?.status === 'done') {
      navigation.goBack();
    }
  }, [navigation, widget?.status]);

  if (!widget) {
    return (
      <View style={[styles.root, { paddingTop: insets.top }]}>
        <Pressable onPress={() => navigation.goBack()} style={styles.back}>
          <Text style={styles.backText}>Назад</Text>
        </Pressable>
        <Text style={styles.missing}>Этого виджета уже нет на крышке.</Text>
      </View>
    );
  }

  const dateLabel = quietDate(instance?.when);
  const chrome = { insets, dateLabel, onBack: () => navigation.goBack() };

  switch (widget.type) {
    case 'counter':
      return <CounterUse widget={widget} cue={cue} chrome={chrome} />;
    case 'tick':
      return <TickUse widget={widget} chrome={chrome} onToggle={() => desk.toggleTick(widget.id)} />;
    case 'reminder':
      return (
        <ReminderUse
          widget={widget}
          latestBy={subject?.window}
          chrome={chrome}
          onComplete={() => desk.completeReminder(widget.id)}
          onSaveWindow={(hours, minutes) => desk.setReminderWindow(widget.id, hours, minutes)}
          onDogfood={() => desk.fireDogfoodReminder(widget.id)}
        />
      );
    case 'checklist':
    case 'timer':
    case 'stepper':
      return (
        <View style={[styles.root, { paddingTop: insets.top }]}>
          <Pressable onPress={() => navigation.goBack()} style={styles.back}>
            <Text style={styles.backText}>Назад</Text>
          </Pressable>
          <Text style={styles.missing}>Этот тип ещё не открывается.</Text>
        </View>
      );
    default: {
      const exhaustive: never = widget.type;
      return exhaustive;
    }
  }
}

type Chrome = {
  insets: { top: number; bottom: number };
  dateLabel: string;
  onBack: () => void;
};

function UseBar({ chrome }: { chrome: Chrome }) {
  return (
    <View style={styles.bar}>
      <Pressable onPress={chrome.onBack} hitSlop={12} style={styles.back}>
        <Text style={styles.backText}>Назад</Text>
      </Pressable>
      <Text style={styles.date}>{chrome.dateLabel}</Text>
      <View style={styles.back} />
    </View>
  );
}

function CounterUse({
  widget,
  cue,
  chrome,
}: {
  widget: Widget;
  cue?: Cue;
  chrome: Chrome;
}) {
  const desk = useDesk();
  const [cueDraft, setCueDraft] = useState(cue?.text ?? '');
  const [goalDraft, setGoalDraft] = useState(String(widget.payload.target ?? ''));

  useEffect(() => {
    if (cue) setCueDraft(cue.text);
  }, [cue]);

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
      style={[styles.root, { paddingTop: chrome.insets.top }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <UseBar chrome={chrome} />
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
          style={({ pressed }) => [styles.step, pressed && styles.pressed]}
          accessibilityLabel="минус"
        >
          <Text style={styles.stepText}>−</Text>
        </Pressable>
        <Pressable
          onPress={() => desk.tickCounter(widget.id, 1)}
          style={({ pressed }) => [styles.step, styles.stepPlus, pressed && styles.pressed]}
          accessibilityLabel="плюс"
        >
          <Text style={[styles.stepText, styles.stepPlusText]}>+</Text>
        </Pressable>
      </View>

      <Pressable
        onPress={() => desk.completeCounter(widget.id)}
        style={({ pressed }) => [
          styles.done,
          { marginBottom: chrome.insets.bottom + spacing.md },
          pressed && styles.pressed,
        ]}
      >
        <Text style={styles.doneText}>Готово</Text>
      </Pressable>
    </KeyboardAvoidingView>
  );
}

function TickUse({
  widget,
  chrome,
  onToggle,
}: {
  widget: Widget;
  chrome: Chrome;
  onToggle: () => void;
}) {
  const done = Boolean(widget.payload.done);
  return (
    <View style={[styles.root, { paddingTop: chrome.insets.top }]}>
      <UseBar chrome={chrome} />
      <Text style={styles.title}>{widget.title}</Text>
      <View style={styles.tickBlock}>
        <View style={styles.tickGroup}>
          <Pressable
            onPress={onToggle}
            style={({ pressed }) => [styles.useBox, done && styles.useBoxDone, pressed && styles.pressed]}
            accessibilityLabel="галочка"
          >
            <Text style={[styles.useCheck, done && styles.useCheckDone]}>{done ? '✓' : ''}</Text>
          </Pressable>
          <Text style={styles.tickHint}>на Сегодня</Text>
        </View>
      </View>
    </View>
  );
}

function ReminderUse({
  widget,
  latestBy,
  chrome,
  onComplete,
  onSaveWindow,
  onDogfood,
}: {
  widget: Widget;
  latestBy: Window | null | undefined;
  chrome: Chrome;
  onComplete: () => void;
  onSaveWindow: (hours: number, minutes: number) => Promise<void>;
  onDogfood: () => Promise<void>;
}) {
  const [whenOpen, setWhenOpen] = useState(false);
  const clock = useMemo(
    () => clockPartsFromWindow(latestBy, widget.payload.fire_at),
    [latestBy, widget.payload.fire_at],
  );
  const fireClock = formatFireClock(widget.payload.fire_at);

  return (
    <View style={[styles.root, { paddingTop: chrome.insets.top }]}>
      <UseBar chrome={chrome} />
      <Text style={styles.title}>{widget.title}</Text>

      <Pressable
        onPress={() => setWhenOpen(true)}
        style={({ pressed }) => [styles.clockHit, pressed && styles.pressed]}
        accessibilityLabel="во сколько напомнить"
      >
        <Text style={styles.number}>{fireClock || '—'}</Text>
      </Pressable>
      <Pressable
        onPress={() => setWhenOpen(true)}
        style={({ pressed }) => [styles.whenLink, pressed && styles.pressed]}
      >
        <Text style={styles.whenLinkText}>во сколько</Text>
      </Pressable>

      <Pressable
        onPress={onComplete}
        style={({ pressed }) => [
          styles.done,
          { marginBottom: chrome.insets.bottom + spacing.md },
          pressed && styles.pressed,
        ]}
      >
        <Text style={styles.doneText}>Я проехал</Text>
      </Pressable>

      <WhenModal
        visible={whenOpen}
        initialHours={clock.hours}
        initialMinutes={clock.minutes}
        onClose={() => setWhenOpen(false)}
        onSave={(hours, minutes) => {
          void onSaveWindow(hours, minutes);
          setWhenOpen(false);
        }}
        onDogfood={() => {
          void onDogfood();
        }}
      />
    </View>
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
  tickBlock: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.xl,
  },
  tickGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  useBox: {
    width: 60,
    height: 60,
    borderRadius: radii.sm,
    borderWidth: 2,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.white,
  },
  useBoxDone: {
    backgroundColor: colors.primary,
  },
  useCheck: {
    fontSize: 32,
    fontWeight: '700',
    color: colors.primary,
  },
  useCheckDone: {
    color: colors.white,
  },
  tickHint: {
    ...typography.caption,
    color: colors.textMuted,
  },
  clockHit: {
    alignItems: 'center',
    marginTop: spacing.xl,
  },
  whenLink: {
    alignItems: 'center',
    marginTop: spacing.sm,
    paddingVertical: spacing.sm,
  },
  whenLinkText: {
    ...typography.subtitle,
    color: colors.primary,
  },
  pressed: {
    opacity: 0.7,
  },
});
