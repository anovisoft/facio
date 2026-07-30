import React, { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { CounterResponse, TimerResponse, TimerSignal } from '@/api/types';
import {
  cancelScheduledNotification,
  scheduleTimerNotification,
  signalTimerComplete,
} from '@/services/timerSignals';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type TimerStackProps = {
  timers: TimerResponse[];
  /** Preview (draft/accept): visible, no start. */
  interactive?: boolean;
  disabled?: boolean;
  onCompleteTimer?: (timerId: string) => void;
};

type RunningState = {
  endsAt: number;
  notificationId: string | null;
};

function formatRemaining(sec: number): string {
  const s = Math.max(0, Math.ceil(sec));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, '0')}`;
}

function formatDuration(sec: number): string {
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const r = sec % 60;
  return r === 0 ? `${m}m` : `${m}m ${r}s`;
}

function signalLabel(
  signal: TimerSignal,
  t: (key: string) => string,
): string {
  switch (signal) {
    case 'nudge':
      return t('plugins.signalNudge');
    case 'alert':
      return t('plugins.signalAlert');
    default: {
      const _exhaustive: never = signal;
      return _exhaustive;
    }
  }
}

export function TimerStack({
  timers,
  interactive = false,
  disabled = false,
  onCompleteTimer,
}: TimerStackProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [now, setNow] = useState(() => Date.now());
  const [running, setRunning] = useState<Record<string, RunningState>>({});
  const firedRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (Object.keys(running).length === 0) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [running]);

  useEffect(() => {
    for (const timer of timers) {
      const run = running[timer.id];
      if (!run) continue;
      if (now < run.endsAt) continue;
      if (firedRef.current.has(timer.id)) continue;
      firedRef.current.add(timer.id);
      void (async () => {
        await cancelScheduledNotification(run.notificationId);
        await signalTimerComplete(timer.title, timer.signal);
        onCompleteTimer?.(timer.id);
        setRunning((prev) => {
          const next = { ...prev };
          delete next[timer.id];
          return next;
        });
      })();
    }
  }, [now, running, timers, onCompleteTimer]);

  if (timers.length === 0) return null;

  const startTimer = async (timer: TimerResponse) => {
    if (!interactive || disabled || timer.completed || running[timer.id]) {
      return;
    }
    const endsAt = Date.now() + timer.duration_sec * 1000;
    firedRef.current.delete(timer.id);
    const notificationId = await scheduleTimerNotification(
      timer.id,
      timer.title,
      timer.signal,
      endsAt,
    );
    setRunning((prev) => ({
      ...prev,
      [timer.id]: { endsAt, notificationId },
    }));
  };

  const stopTimer = async (timerId: string) => {
    const run = running[timerId];
    await cancelScheduledNotification(run?.notificationId);
    setRunning((prev) => {
      const next = { ...prev };
      delete next[timerId];
      return next;
    });
  };

  return (
    <View style={styles.root}>
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('plugins.timers')}
      </Text>
      {timers.map((timer) => {
        const run = running[timer.id];
        const remaining = run
          ? (run.endsAt - now) / 1000
          : timer.duration_sec;
        const canStart =
          interactive && !disabled && !timer.completed && !run;

        return (
          <View
            key={timer.id}
            style={[
              styles.row,
              {
                borderColor: colors.border,
                backgroundColor: colors.surface,
                opacity: timer.completed ? 0.55 : 1,
              },
            ]}
          >
            <View style={styles.meta}>
              <Text style={[styles.title, { color: colors.text }]}>
                {timer.title}
              </Text>
              <Text style={[styles.caption, { color: colors.textSecondary }]}>
                {signalLabel(timer.signal, t)}
                {' · '}
                {run
                  ? formatRemaining(remaining)
                  : formatDuration(timer.duration_sec)}
                {timer.completed ? ` · ${t('plugins.timerDone')}` : ''}
              </Text>
            </View>
            {interactive ? (
              run ? (
                <Pressable
                  disabled={disabled}
                  onPress={() => void stopTimer(timer.id)}
                  style={[styles.btn, { borderColor: colors.border }]}
                >
                  <Text style={{ color: colors.text }}>{t('plugins.stop')}</Text>
                </Pressable>
              ) : (
                <Pressable
                  disabled={!canStart}
                  onPress={() => void startTimer(timer)}
                  style={[
                    styles.btn,
                    {
                      borderColor: colors.primary,
                      opacity: canStart ? 1 : 0.4,
                    },
                  ]}
                >
                  <Text style={{ color: colors.primary }}>
                    {timer.completed
                      ? t('plugins.timerDone')
                      : t('plugins.start')}
                  </Text>
                </Pressable>
              )
            ) : (
              <Text style={[styles.previewBadge, { color: colors.textMuted }]}>
                {formatDuration(timer.duration_sec)}
              </Text>
            )}
          </View>
        );
      })}
    </View>
  );
}

type CounterControlProps = {
  counter: CounterResponse;
  interactive?: boolean;
  disabled?: boolean;
  onChange?: (nextCurrent: number) => void;
};

export function CounterControl({
  counter,
  interactive = false,
  disabled = false,
  onChange,
}: CounterControlProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const step = counter.step > 0 ? counter.step : 1;
  const label = counter.label?.trim() || t('plugins.counter');

  const bump = (delta: number) => {
    if (!interactive || disabled) return;
    const next = Math.max(
      0,
      Math.min(counter.target, counter.current + delta),
    );
    if (next === counter.current) return;
    onChange?.(next);
  };

  return (
    <View
      style={[
        styles.counterCard,
        { borderColor: colors.border, backgroundColor: colors.surface },
      ]}
    >
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {label}
      </Text>
      <View style={styles.counterRow}>
        {interactive ? (
          <Pressable
            disabled={disabled || counter.current <= 0}
            onPress={() => bump(-step)}
            style={[
              styles.counterBtn,
              {
                borderColor: colors.border,
                opacity: disabled || counter.current <= 0 ? 0.35 : 1,
              },
            ]}
          >
            <Text style={[styles.counterBtnText, { color: colors.text }]}>
              −
            </Text>
          </Pressable>
        ) : null}
        <Text style={[styles.counterValue, { color: colors.text }]}>
          {counter.current}
          <Text style={{ color: colors.textSecondary }}>
            {' '}
            / {counter.target}
          </Text>
        </Text>
        {interactive ? (
          <Pressable
            disabled={disabled || counter.current >= counter.target}
            onPress={() => bump(step)}
            style={[
              styles.counterBtn,
              {
                borderColor: colors.primary,
                opacity:
                  disabled || counter.current >= counter.target ? 0.35 : 1,
              },
            ]}
          >
            <Text style={[styles.counterBtnText, { color: colors.primary }]}>
              +
            </Text>
          </Pressable>
        ) : (
          <Text style={[styles.previewBadge, { color: colors.textMuted }]}>
            {t('plugins.preview')}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.sm,
  },
  sectionLabel: {
    ...typography.label,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  row: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  meta: {
    flex: 1,
    gap: 2,
  },
  title: {
    ...typography.body,
    fontWeight: '600',
  },
  caption: {
    ...typography.caption,
  },
  btn: {
    borderWidth: 1,
    borderRadius: radii.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  previewBadge: {
    ...typography.caption,
  },
  counterCard: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    gap: spacing.sm,
  },
  counterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  counterBtn: {
    width: 44,
    height: 44,
    borderRadius: radii.md,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  counterBtnText: {
    fontSize: 24,
    fontWeight: '600',
    lineHeight: 28,
  },
  counterValue: {
    ...typography.title,
    minWidth: 96,
    textAlign: 'center',
  },
});
