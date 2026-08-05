import React, { useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTranslation } from 'react-i18next';

import type {
  ActionTimelineResponse,
  CounterResponse,
  IntervalPlanResponse,
  StepperBeatResponse,
  StepperResponse,
  TimerResponse,
  TimerSignal,
} from '@/api/types';
import {
  cancelScheduledNotification,
  scheduleTimerNotification,
  signalTimerComplete,
} from '@/services/timerSignals';
import { BlockEditButton } from '@/shared/ui/BlockEditButton';
import { useSessionStore } from '@/store';
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
                  style={[styles.iconBtn, { borderColor: colors.border }]}
                  accessibilityLabel={t('plugins.stop')}
                >
                  <Ionicons name="stop" size={18} color={colors.text} />
                  <Text style={{ color: colors.text }}>{t('plugins.stop')}</Text>
                </Pressable>
              ) : (
                <Pressable
                  disabled={!canStart}
                  onPress={() => void startTimer(timer)}
                  style={[
                    styles.iconBtn,
                    {
                      borderColor: colors.primary,
                      opacity: canStart ? 1 : 0.4,
                    },
                  ]}
                  accessibilityLabel={
                    timer.completed
                      ? t('plugins.timerDone')
                      : t('plugins.start')
                  }
                >
                  <Ionicons
                    name={timer.completed ? 'checkmark' : 'play'}
                    size={18}
                    color={colors.primary}
                  />
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

type TimelineProgressProps = {
  timeline: ActionTimelineResponse;
  interactive?: boolean;
  disabled?: boolean;
};

type TimelineRun = {
  startedAt: number;
  /** Accumulated ms while paused (wall clock adjustment). */
  pausedTotalMs: number;
  pauseStartedAt: number | null;
  notificationId: string | null;
};

export function TimelineProgress({
  timeline,
  interactive = false,
  disabled = false,
}: TimelineProgressProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [now, setNow] = useState(() => Date.now());
  const [run, setRun] = useState<TimelineRun | null>(null);
  const [done, setDone] = useState(false);
  const firedMarkers = useRef<Set<number>>(new Set());

  const markers = [...timeline.markers].sort((a, b) => a.at_sec - b.at_sec);
  const durationSec = Math.max(1, timeline.duration_sec);

  useEffect(() => {
    if (!run || run.pauseStartedAt != null || done) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [run, done]);

  const elapsedSec = (() => {
    if (!run) return 0;
    const pauseExtra =
      run.pauseStartedAt != null ? now - run.pauseStartedAt : 0;
    const ms = now - run.startedAt - run.pausedTotalMs - pauseExtra;
    return Math.max(0, Math.min(durationSec, ms / 1000));
  })();

  const progress = elapsedSec / durationSec;
  const isPaused = run != null && run.pauseStartedAt != null;
  const isRunning = run != null && !isPaused && !done;

  useEffect(() => {
    if (!run || isPaused || done) return;
    for (const marker of markers) {
      if (elapsedSec < marker.at_sec) continue;
      if (firedMarkers.current.has(marker.at_sec)) continue;
      // Skip firing start marker (0) on session start — user already pressed Start.
      if (marker.at_sec === 0 && elapsedSec < 0.5) {
        firedMarkers.current.add(0);
        continue;
      }
      firedMarkers.current.add(marker.at_sec);
      void signalTimerComplete(marker.title, marker.signal);
    }
    if (elapsedSec >= durationSec) {
      setDone(true);
      void cancelScheduledNotification(run.notificationId);
      setRun(null);
    }
  }, [elapsedSec, run, isPaused, done, markers, durationSec]);

  if (markers.length === 0 && timeline.duration_sec < 1) return null;

  const start = async () => {
    if (!interactive || disabled || run) return;
    firedMarkers.current = new Set();
    setDone(false);
    const endsAt = Date.now() + durationSec * 1000;
    const lastAlert =
      [...markers].reverse().find((m) => m.signal === 'alert') ??
      markers[markers.length - 1];
    const notificationId = lastAlert
      ? await scheduleTimerNotification(
          `timeline-${lastAlert.at_sec}`,
          lastAlert.title,
          lastAlert.signal,
          endsAt,
        )
      : null;
    setRun({
      startedAt: Date.now(),
      pausedTotalMs: 0,
      pauseStartedAt: null,
      notificationId,
    });
    setNow(Date.now());
  };

  const pause = async () => {
    if (!run || run.pauseStartedAt != null) return;
    await cancelScheduledNotification(run.notificationId);
    setRun({
      ...run,
      pauseStartedAt: Date.now(),
      notificationId: null,
    });
  };

  const resume = async () => {
    if (!run || run.pauseStartedAt == null) return;
    const pausedTotalMs =
      run.pausedTotalMs + (Date.now() - run.pauseStartedAt);
    const remainingMs = Math.max(
      1000,
      (durationSec - (Date.now() - run.startedAt - pausedTotalMs) / 1000) *
        1000,
    );
    const lastAlert =
      [...markers].reverse().find((m) => m.signal === 'alert') ??
      markers[markers.length - 1];
    const notificationId = lastAlert
      ? await scheduleTimerNotification(
          `timeline-${lastAlert.at_sec}`,
          lastAlert.title,
          lastAlert.signal,
          Date.now() + remainingMs,
        )
      : null;
    setRun({
      ...run,
      pausedTotalMs,
      pauseStartedAt: null,
      notificationId,
    });
    setNow(Date.now());
  };

  const reset = async () => {
    await cancelScheduledNotification(run?.notificationId);
    setRun(null);
    setDone(false);
    firedMarkers.current = new Set();
  };

  return (
    <View
      style={[
        styles.clockCard,
        { borderColor: colors.border, backgroundColor: colors.surface },
      ]}
    >
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('plugins.timeline')}
      </Text>
      <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
        <View
          style={[
            styles.progressFill,
            {
              backgroundColor: colors.primary,
              width: `${Math.round(progress * 100)}%`,
            },
          ]}
        />
        {markers.map((marker) => {
          const left = Math.min(
            100,
            Math.max(0, (marker.at_sec / durationSec) * 100),
          );
          const hit = elapsedSec >= marker.at_sec;
          return (
            <View
              key={`${marker.at_sec}-${marker.title}`}
              style={[
                styles.markerDot,
                {
                  left: `${left}%`,
                  backgroundColor: hit ? colors.primary : colors.textMuted,
                  borderColor: colors.surface,
                },
              ]}
            />
          );
        })}
      </View>
      <Text style={[styles.caption, { color: colors.textSecondary }]}>
        {formatRemaining(done ? 0 : durationSec - elapsedSec)}
        {' · '}
        {formatDuration(durationSec)}
        {done ? ` · ${t('plugins.timerDone')}` : ''}
      </Text>
      <View style={styles.markerList}>
        {markers.map((marker) => {
          const hit = elapsedSec >= marker.at_sec || done;
          return (
            <Text
              key={`label-${marker.at_sec}-${marker.title}`}
              style={[
                styles.caption,
                {
                  color: hit ? colors.text : colors.textSecondary,
                  opacity: hit ? 1 : 0.75,
                },
              ]}
            >
              {formatDuration(marker.at_sec)} · {marker.title}
              {' · '}
              {signalLabel(marker.signal, t)}
            </Text>
          );
        })}
      </View>
      {interactive ? (
        <View style={styles.controlsRow}>
          {!run && !done ? (
            <Pressable
              disabled={disabled}
              onPress={() => void start()}
              style={[styles.iconBtn, { borderColor: colors.primary }]}
              accessibilityLabel={t('plugins.start')}
            >
              <Ionicons name="play" size={18} color={colors.primary} />
              <Text style={{ color: colors.primary }}>{t('plugins.start')}</Text>
            </Pressable>
          ) : null}
          {isRunning ? (
            <Pressable
              disabled={disabled}
              onPress={() => void pause()}
              style={[styles.iconBtn, { borderColor: colors.border }]}
              accessibilityLabel={t('plugins.pause')}
            >
              <Ionicons name="pause" size={18} color={colors.text} />
              <Text style={{ color: colors.text }}>{t('plugins.pause')}</Text>
            </Pressable>
          ) : null}
          {isPaused ? (
            <Pressable
              disabled={disabled}
              onPress={() => void resume()}
              style={[styles.iconBtn, { borderColor: colors.primary }]}
              accessibilityLabel={t('plugins.resume')}
            >
              <Ionicons name="play" size={18} color={colors.primary} />
              <Text style={{ color: colors.primary }}>
                {t('plugins.resume')}
              </Text>
            </Pressable>
          ) : null}
          {run || done ? (
            <Pressable
              disabled={disabled}
              onPress={() => void reset()}
              style={[styles.iconBtn, { borderColor: colors.border }]}
              accessibilityLabel={t('plugins.reset')}
            >
              <Ionicons name="refresh" size={18} color={colors.text} />
              <Text style={{ color: colors.text }}>{t('plugins.reset')}</Text>
            </Pressable>
          ) : null}
        </View>
      ) : (
        <Text style={[styles.previewBadge, { color: colors.textMuted }]}>
          {t('plugins.preview')}
        </Text>
      )}
    </View>
  );
}

type IntervalPlayerProps = {
  plan: IntervalPlanResponse;
  interactive?: boolean;
  disabled?: boolean;
};

type IntervalRun = {
  segmentIndex: number;
  segmentStartedAt: number;
  pausedTotalMs: number;
  pauseStartedAt: number | null;
  notificationId: string | null;
};

export function IntervalPlayer({
  plan,
  interactive = false,
  disabled = false,
}: IntervalPlayerProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [now, setNow] = useState(() => Date.now());
  const [run, setRun] = useState<IntervalRun | null>(null);
  const [done, setDone] = useState(false);
  const segments = plan.segments;

  useEffect(() => {
    if (!run || run.pauseStartedAt != null || done) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [run, done]);

  const current =
    segments.length === 0
      ? null
      : run
        ? segments[run.segmentIndex]
        : segments[0];
  const segmentElapsed = (() => {
    if (!run || !current) return 0;
    const pauseExtra =
      run.pauseStartedAt != null ? now - run.pauseStartedAt : 0;
    const ms = now - run.segmentStartedAt - run.pausedTotalMs - pauseExtra;
    return Math.max(0, ms / 1000);
  })();
  const remaining = current
    ? Math.max(0, current.duration_sec - segmentElapsed)
    : 0;
  const isPaused = run != null && run.pauseStartedAt != null;
  const isRunning = run != null && !isPaused && !done;

  useEffect(() => {
    if (!run || isPaused || done || !current) return;
    if (segmentElapsed < current.duration_sec) return;
    void (async () => {
      await cancelScheduledNotification(run.notificationId);
      await signalTimerComplete(current.title, current.signal);
      const nextIndex = run.segmentIndex + 1;
      if (nextIndex >= segments.length) {
        setDone(true);
        setRun(null);
        return;
      }
      const next = segments[nextIndex];
      const endsAt = Date.now() + next.duration_sec * 1000;
      const notificationId = await scheduleTimerNotification(
        `interval-${nextIndex}`,
        next.title,
        next.signal,
        endsAt,
      );
      setRun({
        segmentIndex: nextIndex,
        segmentStartedAt: Date.now(),
        pausedTotalMs: 0,
        pauseStartedAt: null,
        notificationId,
      });
      setNow(Date.now());
    })();
  }, [segmentElapsed, run, isPaused, done, current, segments]);

  if (segments.length === 0) return null;

  const start = async () => {
    if (!interactive || disabled || run) return;
    setDone(false);
    const first = segments[0];
    const endsAt = Date.now() + first.duration_sec * 1000;
    const notificationId = await scheduleTimerNotification(
      'interval-0',
      first.title,
      first.signal,
      endsAt,
    );
    setRun({
      segmentIndex: 0,
      segmentStartedAt: Date.now(),
      pausedTotalMs: 0,
      pauseStartedAt: null,
      notificationId,
    });
    setNow(Date.now());
  };

  const pause = async () => {
    if (!run || run.pauseStartedAt != null) return;
    await cancelScheduledNotification(run.notificationId);
    setRun({
      ...run,
      pauseStartedAt: Date.now(),
      notificationId: null,
    });
  };

  const resume = async () => {
    if (!run || run.pauseStartedAt == null || !current) return;
    const pausedTotalMs =
      run.pausedTotalMs + (Date.now() - run.pauseStartedAt);
    const remainingMs = Math.max(
      1000,
      (current.duration_sec -
        (Date.now() - run.segmentStartedAt - pausedTotalMs) / 1000) *
        1000,
    );
    const notificationId = await scheduleTimerNotification(
      `interval-${run.segmentIndex}`,
      current.title,
      current.signal,
      Date.now() + remainingMs,
    );
    setRun({
      ...run,
      pausedTotalMs,
      pauseStartedAt: null,
      notificationId,
    });
    setNow(Date.now());
  };

  const reset = async () => {
    await cancelScheduledNotification(run?.notificationId);
    setRun(null);
    setDone(false);
  };

  const segmentProgress = current
    ? Math.min(1, segmentElapsed / Math.max(1, current.duration_sec))
    : 0;

  return (
    <View
      style={[
        styles.clockCard,
        { borderColor: colors.border, backgroundColor: colors.surface },
      ]}
    >
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('plugins.interval')}
      </Text>
      <Text style={[styles.title, { color: colors.text }]}>
        {done
          ? t('plugins.timerDone')
          : current
            ? current.title
            : t('plugins.interval')}
      </Text>
      <Text style={[styles.caption, { color: colors.textSecondary }]}>
        {run
          ? t('plugins.segmentOf', {
              current: run.segmentIndex + 1,
              total: segments.length,
            })
          : t('plugins.segmentOf', {
              current: 1,
              total: segments.length,
            })}
        {' · '}
        {done
          ? formatDuration(0)
          : run
            ? formatRemaining(remaining)
            : formatDuration(current?.duration_sec ?? 0)}
      </Text>
      <View style={[styles.progressTrack, { backgroundColor: colors.border }]}>
        <View
          style={[
            styles.progressFill,
            {
              backgroundColor: colors.primary,
              width: `${Math.round((done ? 1 : segmentProgress) * 100)}%`,
            },
          ]}
        />
      </View>
      <View style={styles.markerList}>
        {segments.map((segment, index) => {
          const past = done || (run != null && index < run.segmentIndex);
          const active = run != null && index === run.segmentIndex && !done;
          return (
            <Text
              key={`seg-${index}-${segment.title}`}
              style={[
                styles.caption,
                {
                  color: active || past ? colors.text : colors.textSecondary,
                  fontWeight: active ? '600' : '400',
                },
              ]}
            >
              {index + 1}. {segment.title} ·{' '}
              {formatDuration(segment.duration_sec)}
            </Text>
          );
        })}
      </View>
      {interactive ? (
        <View style={styles.controlsRow}>
          {!run && !done ? (
            <Pressable
              disabled={disabled}
              onPress={() => void start()}
              style={[styles.btn, { borderColor: colors.primary }]}
            >
              <Text style={{ color: colors.primary }}>{t('plugins.start')}</Text>
            </Pressable>
          ) : null}
          {isRunning ? (
            <Pressable
              disabled={disabled}
              onPress={() => void pause()}
              style={[styles.btn, { borderColor: colors.border }]}
            >
              <Text style={{ color: colors.text }}>{t('plugins.pause')}</Text>
            </Pressable>
          ) : null}
          {isPaused ? (
            <Pressable
              disabled={disabled}
              onPress={() => void resume()}
              style={[styles.btn, { borderColor: colors.primary }]}
            >
              <Text style={{ color: colors.primary }}>
                {t('plugins.resume')}
              </Text>
            </Pressable>
          ) : null}
          {run || done ? (
            <Pressable
              disabled={disabled}
              onPress={() => void reset()}
              style={[styles.btn, { borderColor: colors.border }]}
            >
              <Text style={{ color: colors.text }}>{t('plugins.reset')}</Text>
            </Pressable>
          ) : null}
        </View>
      ) : (
        <Text style={[styles.previewBadge, { color: colors.textMuted }]}>
          {t('plugins.preview')}
        </Text>
      )}
    </View>
  );
}

type CounterControlProps = {
  counter: CounterResponse;
  interactive?: boolean;
  disabled?: boolean;
  onChange?: (nextCurrent: number) => void;
  /** Manual entry for this counter Block (E2b-iterate #12). */
  onEdit?: () => void;
};

export function CounterControl({
  counter,
  interactive = false,
  disabled = false,
  onChange,
  onEdit,
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
      <View style={styles.blockHeader}>
        <Text
          style={[
            styles.sectionLabel,
            styles.blockHeaderLabel,
            { color: colors.textMuted },
          ]}
        >
          {label}
        </Text>
        {onEdit ? <BlockEditButton onPress={onEdit} /> : null}
      </View>
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

type StepperPlayerProps = {
  stepper: StepperResponse;
  interactive?: boolean;
  disabled?: boolean;
  /** Persist work/measure counter for the current beat. */
  onBeatCounterChange?: (beatId: string, nextCurrent: number) => void;
  /** Compact strip-only mode for sticky stage. */
  compact?: boolean;
  /**
   * Action id for same-calendar-day beatIndex / rest resume (D2).
   * Omit in preview / Hero contexts.
   */
  actionId?: string;
  /** Manual entry for this stepper Block (E2b-iterate #12). */
  onEdit?: () => void;
};

function formatMmSs(totalSec: number): string {
  const sec = Math.max(0, Math.ceil(totalSec));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function hydrateStepperState(
  actionId: string | undefined,
  beats: StepperBeatResponse[],
) {
  const beatCount = beats.length;
  if (!actionId || beatCount < 1) {
    return { beatIndex: 0, sessionDone: false, rest: null as null };
  }
  const saved = useSessionStore.getState().getBlockRuntime(actionId);
  if (!saved) {
    return { beatIndex: 0, sessionDone: false, rest: null as null };
  }
  const beatIndex = Math.min(
    Math.max(0, saved.beatIndex),
    Math.max(0, beatCount - 1),
  );
  const sessionDone = Boolean(saved.sessionDone) && beatIndex >= beatCount - 1;
  let rest: {
    startedAt: number;
    durationSec: number;
    notificationId: string | null;
    beatId: string;
  } | null = null;
  const beat = beats[beatIndex];
  if (
    saved.rest &&
    !sessionDone &&
    beat &&
    saved.rest.beatId === beat.id &&
    beat.kind === 'rest'
  ) {
    const remaining =
      saved.rest.durationSec - (Date.now() - saved.rest.startedAt) / 1000;
    if (remaining > 0.4) {
      rest = {
        startedAt: saved.rest.startedAt,
        durationSec: saved.rest.durationSec,
        notificationId: null,
        beatId: saved.rest.beatId,
      };
    }
  }
  return { beatIndex, sessionDone, rest };
}

export function StepperPlayer({
  stepper,
  interactive = false,
  disabled = false,
  onBeatCounterChange,
  compact = false,
  actionId,
  onEdit,
}: StepperPlayerProps) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setBlockRuntime = useSessionStore((s) => s.setBlockRuntime);
  const beats = stepper.beats ?? [];
  const hydratedRef = useRef(false);
  const initial = useRef(hydrateStepperState(actionId, beats)).current;
  const [beatIndex, setBeatIndex] = useState(initial.beatIndex);
  const [restRun, setRestRun] = useState<{
    startedAt: number;
    durationSec: number;
    notificationId: string | null;
    beatId?: string;
  } | null>(initial.rest);
  const [now, setNow] = useState(() => Date.now());
  const [sessionDone, setSessionDone] = useState(initial.sessionDone);

  const safeIndex = Math.min(beatIndex, Math.max(0, beats.length - 1));
  const current: StepperBeatResponse | null =
    beats.length === 0 ? null : beats[safeIndex];
  const canGoBack = interactive && !disabled && (safeIndex > 0 || sessionDone);

  useEffect(() => {
    if (!restRun) return;
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, [restRun]);

  const restRemaining = restRun
    ? Math.max(0, restRun.durationSec - (now - restRun.startedAt) / 1000)
    : 0;

  useEffect(() => {
    if (!restRun || restRemaining > 0) return;
    void (async () => {
      await cancelScheduledNotification(restRun.notificationId);
      const beat = beats[safeIndex];
      if (beat) {
        await signalTimerComplete(beat.title, beat.signal ?? 'nudge');
      }
      setRestRun(null);
    })();
  }, [restRemaining, restRun, beats, safeIndex]);

  // Persist beat position / rest wall-clock for same-day leave→return (D2).
  useEffect(() => {
    if (!actionId || !interactive) return;
    // Skip first paint write if we just hydrated (avoid clobber before mount settle).
    if (!hydratedRef.current) {
      hydratedRef.current = true;
      return;
    }
    const beat = beats[safeIndex];
    const rest =
      restRun && beat
        ? {
            beatId: restRun.beatId ?? beat.id,
            startedAt: restRun.startedAt,
            durationSec: restRun.durationSec,
          }
        : null;
    setBlockRuntime(actionId, {
      beatIndex: safeIndex,
      sessionDone,
      rest,
    });
  }, [
    actionId,
    interactive,
    safeIndex,
    sessionDone,
    restRun,
    beats,
    setBlockRuntime,
  ]);

  if (beats.length === 0) return null;

  const clearRest = () => {
    void cancelScheduledNotification(restRun?.notificationId ?? null);
    setRestRun(null);
  };

  const goNext = () => {
    if (!interactive || disabled) return;
    clearRest();
    if (safeIndex + 1 >= beats.length) {
      setSessionDone(true);
      return;
    }
    setBeatIndex(safeIndex + 1);
    setSessionDone(false);
  };

  const goBack = () => {
    if (!canGoBack) return;
    clearRest();
    if (sessionDone) {
      setSessionDone(false);
      setBeatIndex(Math.max(0, beats.length - 1));
      return;
    }
    setBeatIndex(Math.max(0, safeIndex - 1));
  };

  const startRest = async () => {
    if (!interactive || disabled || !current || current.kind !== 'rest') return;
    if (restRun) return;
    const duration = current.duration_sec ?? 0;
    if (duration < 1) return;
    const endsAt = Date.now() + duration * 1000;
    const notificationId = await scheduleTimerNotification(
      `stepper-${current.id}`,
      current.title,
      current.signal ?? 'nudge',
      endsAt,
    );
    setRestRun({
      startedAt: Date.now(),
      durationSec: duration,
      notificationId,
      beatId: current.id,
    });
    setNow(Date.now());
  };

  const navRow = interactive ? (
    <View style={styles.stepNavRow}>
      <Pressable
        disabled={!canGoBack}
        onPress={goBack}
        style={[
          styles.iconBtn,
          styles.stepNavBtn,
          {
            borderColor: colors.border,
            opacity: canGoBack ? 1 : 0.35,
          },
        ]}
        accessibilityLabel={t('plugins.prevBeat')}
      >
        <Ionicons name="chevron-back" size={20} color={colors.text} />
        <Text style={{ color: colors.text }}>{t('plugins.prevBeat')}</Text>
      </Pressable>
      <Pressable
        disabled={disabled || sessionDone}
        onPress={goNext}
        style={[
          styles.iconBtn,
          styles.stepNavBtn,
          {
            borderColor: colors.primary,
            opacity: disabled || sessionDone ? 0.35 : 1,
          },
        ]}
        accessibilityLabel={t('plugins.nextBeat')}
      >
        <Text style={{ color: colors.primary }}>{t('plugins.nextBeat')}</Text>
        <Ionicons name="chevron-forward" size={20} color={colors.primary} />
      </Pressable>
    </View>
  ) : null;

  const strip = (
    <View style={styles.beatStrip}>
      {beats.map((beat, index) => {
        const active = index === safeIndex && !sessionDone;
        const past = index < safeIndex || sessionDone;
        return (
          <View
            key={beat.id || `b${index}`}
            style={[
              styles.beatDot,
              {
                backgroundColor: active
                  ? colors.primary
                  : past
                    ? colors.border
                    : colors.surface,
                borderColor: active ? colors.primary : colors.border,
              },
            ]}
          />
        );
      })}
    </View>
  );

  if (compact) {
    return (
      <View
        style={[
          styles.stepperCompact,
          { borderColor: colors.border, backgroundColor: colors.surface },
        ]}
      >
        {onEdit ? (
          <View style={styles.blockHeader}>
            <Text
              style={[
                styles.sectionLabel,
                styles.blockHeaderLabel,
                { color: colors.textMuted },
              ]}
            >
              {t('plugins.stepper')}
            </Text>
            <BlockEditButton onPress={onEdit} />
          </View>
        ) : null}
        {strip}
        <Text style={[styles.title, { color: colors.text }]} numberOfLines={1}>
          {sessionDone
            ? t('plugins.timerDone')
            : current?.title ?? t('plugins.stepper')}
        </Text>
        {current?.kind === 'rest' && restRun ? (
          <Text style={[styles.clockBig, { color: colors.primary }]}>
            {formatMmSs(restRemaining)}
          </Text>
        ) : current?.counter ? (
          <Text style={[styles.counterValue, { color: colors.text }]}>
            {current.counter.current}
            <Text style={{ color: colors.textSecondary }}>
              {' '}
              / {current.counter.target}
            </Text>
          </Text>
        ) : null}
      </View>
    );
  }

  return (
    <View
      style={[
        styles.stepperCard,
        { borderColor: colors.border, backgroundColor: colors.surface },
      ]}
    >
      <View style={styles.blockHeader}>
        <Text
          style={[
            styles.sectionLabel,
            styles.blockHeaderLabel,
            { color: colors.textMuted },
          ]}
        >
          {t('plugins.stepper')}
        </Text>
        {onEdit ? <BlockEditButton onPress={onEdit} /> : null}
      </View>
      {strip}
      <Text style={[styles.beatMeta, { color: colors.textSecondary }]}>
        {sessionDone
          ? t('plugins.timerDone')
          : t('plugins.segmentOf', {
              current: safeIndex + 1,
              total: beats.length,
            })}
      </Text>
      {!sessionDone && current ? (
        <>
          <Text style={[styles.beatTitle, { color: colors.text }]}>
            {current.title}
          </Text>
          {current.kind === 'rest' ? (
            <View style={styles.restBlock}>
              <Text style={[styles.clockBig, { color: colors.primary }]}>
                {restRun
                  ? formatMmSs(restRemaining)
                  : formatMmSs(current.duration_sec ?? 0)}
              </Text>
              {interactive ? (
                <View style={styles.clockActions}>
                  {!restRun ? (
                    <Pressable
                      disabled={disabled}
                      onPress={() => void startRest()}
                      style={[styles.iconBtn, { borderColor: colors.primary }]}
                      accessibilityLabel={t('plugins.start')}
                    >
                      <Ionicons name="play" size={18} color={colors.primary} />
                      <Text style={{ color: colors.primary }}>
                        {t('plugins.start')}
                      </Text>
                    </Pressable>
                  ) : null}
                </View>
              ) : (
                <Text style={[styles.previewBadge, { color: colors.textMuted }]}>
                  {t('plugins.preview')}
                </Text>
              )}
            </View>
          ) : current.counter ? (
            <View style={styles.workBlock}>
              <CounterControl
                counter={current.counter}
                interactive={interactive}
                disabled={disabled}
                onChange={(next) =>
                  onBeatCounterChange?.(current.id, next)
                }
              />
            </View>
          ) : interactive ? null : (
            <Text style={[styles.previewBadge, { color: colors.textMuted }]}>
              {t('plugins.preview')}
            </Text>
          )}
          {navRow}
        </>
      ) : sessionDone ? (
        navRow
      ) : null}
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
  blockHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  blockHeaderLabel: {
    marginBottom: 0,
    flex: 1,
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
  iconBtn: {
    borderWidth: 1,
    borderRadius: radii.sm,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  stepNavRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.sm,
  },
  stepNavBtn: {
    flex: 1,
    justifyContent: 'center',
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
  clockCard: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    gap: spacing.sm,
  },
  progressTrack: {
    height: 10,
    borderRadius: 5,
    overflow: 'hidden',
    position: 'relative',
  },
  progressFill: {
    height: '100%',
    borderRadius: 5,
  },
  markerDot: {
    position: 'absolute',
    top: -2,
    width: 14,
    height: 14,
    marginLeft: -7,
    borderRadius: 7,
    borderWidth: 2,
  },
  markerList: {
    gap: 2,
  },
  controlsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  counterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  counterBtn: {
    width: 52,
    height: 52,
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
    fontSize: 36,
    lineHeight: 42,
    minWidth: 112,
    textAlign: 'center',
  },
  stepperCard: {
    borderWidth: 1,
    borderRadius: radii.lg,
    padding: spacing.lg,
    gap: spacing.md,
    minHeight: 300,
  },
  stepperCompact: {
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    gap: spacing.xs,
    flexDirection: 'row',
    alignItems: 'center',
  },
  beatStrip: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  beatDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 1,
  },
  beatMeta: {
    ...typography.caption,
  },
  beatTitle: {
    ...typography.hero,
    fontSize: 24,
    lineHeight: 30,
  },
  restBlock: {
    gap: spacing.md,
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  workBlock: {
    gap: spacing.sm,
  },
  clockBig: {
    ...typography.title,
    fontSize: 48,
    lineHeight: 56,
    fontVariant: ['tabular-nums'],
  },
  clockActions: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    justifyContent: 'center',
  },
  nextBtn: {
    alignSelf: 'stretch',
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
});
