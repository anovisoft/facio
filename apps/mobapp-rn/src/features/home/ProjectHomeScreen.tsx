import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import {
  completeAction,
  completeTimer,
  skipAction,
  toggleChecklistItem,
  updateCounter,
  updateStepperBeatCounter,
} from '@/api/actions';
import { getProject, rematerializePlugins, repairProject, completeCycle, startNextCycle } from '@/api/projects';
import { ApiError, type DayKind, type ProjectDetail, type RepairIntent } from '@/api/types';
import { FinishCycleSheet } from '@/features/home/FinishCycleSheet';
import { NextCycleSheet } from '@/features/home/NextCycleSheet';
import { RepairSheet } from '@/features/home/RepairSheet';
import type { RootScreenProps } from '@/navigation/types';
import { trackActionShown } from '@/services/beacons';
import { classifyUnlockDate } from '@/services/localDate';
import { AsyncState } from '@/shared/ui/AsyncState';
import {
  CounterControl,
  IntervalPlayer,
  StepperPlayer,
  TimelineProgress,
  TimerStack,
} from '@/shared/ui/ActionPlugins';
import { ChecklistList } from '@/shared/ui/ChecklistList';
import {
  GLASS_ICON_CHIP_SIZE,
  GlassIconButton,
} from '@/shared/ui/GlassIconButton';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { WhyHero } from '@/shared/ui/WhyHero';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

/** Brief non-blocking Done flash — no modal / progress bar (D iterate). */
const DONE_FLASH_MS = 1800;

/** Session screen (Facio 0.1) — ProjectHomeScreen alias. */
export function ProjectHomeScreen({
  navigation,
  route,
}: RootScreenProps<'Session'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId } = route.params;
  const clearBlockRuntime = useSessionStore((s) => s.clearBlockRuntime);

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [doneFlash, setDoneFlash] = useState<string | null>(null);
  const [repairSheetVisible, setRepairSheetVisible] = useState(false);
  const [repairSummary, setRepairSummary] = useState<string | null>(null);
  const [nextCycleSheetVisible, setNextCycleSheetVisible] = useState(false);
  const [finishCycleSheetVisible, setFinishCycleSheetVisible] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const shownActionIdRef = useRef<string | null>(null);
  const doneFlashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const openGuide = useCallback(() => {
    navigation.navigate('Guide', { projectId, fromSession: true });
  }, [navigation, projectId]);

  const showDoneFlash = useCallback((message: string) => {
    setDoneFlash(message);
    if (doneFlashTimerRef.current) clearTimeout(doneFlashTimerRef.current);
    doneFlashTimerRef.current = setTimeout(() => {
      setDoneFlash(null);
      doneFlashTimerRef.current = null;
    }, DONE_FLASH_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (doneFlashTimerRef.current) clearTimeout(doneFlashTimerRef.current);
    };
  }, []);

  useLayoutEffect(() => {
    navigation.setOptions({
      title:
        project?.title ||
        project?.outcome ||
        project?.paraphrase ||
        t('home.today'),
      headerRight: () => (
        <GlassIconButton
          variant="header"
          onPress={openGuide}
          accessibilityLabel={t('home.menuPath')}
          size={GLASS_ICON_CHIP_SIZE}
        >
          <Ionicons name="menu-outline" size={22} color={colors.text} />
        </GlassIconButton>
      ),
    });
  }, [
    navigation,
    project?.title,
    project?.outcome,
    project?.paraphrase,
    openGuide,
    t,
    colors.text,
  ]);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const detail = await getProject(projectId, controller.signal);
      setProject(detail);
      const nextId = detail.next_action?.id ?? null;
      if (nextId && shownActionIdRef.current !== nextId) {
        shownActionIdRef.current = nextId;
        trackActionShown(projectId, nextId);
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof ApiError ? e.message : t('home.error'));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [projectId, t]);

  useFocusEffect(
    useCallback(() => {
      void load();
      return () => abortRef.current?.abort();
    }, [load]),
  );

  // Poll while phase-3 plugins are still materializing after Start.
  useEffect(() => {
    if (
      !project ||
      project.plugins_ready !== false ||
      project.plugins_error ||
      busy
    ) {
      return;
    }
    const timer = setInterval(() => {
      void (async () => {
        try {
          const detail = await getProject(projectId);
          setProject(detail);
        } catch {
          // Keep showing loader; next tick retries.
        }
      })();
    }, 1500);
    return () => clearInterval(timer);
  }, [project, busy, projectId]);

  const onRetryPlugins = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const detail = await rematerializePlugins(projectId);
      setProject(detail);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.pluginsError'));
    } finally {
      setBusy(false);
    }
  }, [projectId, t]);

  const refreshAfterMutation = async () => {
    const detail = await getProject(projectId);
    setProject(detail);
    const nextId = detail.next_action?.id ?? null;
    if (nextId && shownActionIdRef.current !== nextId) {
      shownActionIdRef.current = nextId;
      trackActionShown(projectId, nextId);
    }
    return detail;
  };

  const onComplete = async () => {
    if (!project?.next_action || busy) return;
    const action = project.next_action;

    const incomplete = action.checklist_items.filter((i) => !i.done);
    if (incomplete.length > 0) {
      setError(t('home.checklistRequired', { count: incomplete.length }));
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await completeAction(action.id);
      clearBlockRuntime(action.id);
      const detail = await refreshAfterMutation();
      // D iterate: next executable Session stays in-Guide; else Continue.
      if (detail.next_action) {
        const nextTitle = detail.next_action.title?.trim();
        showDoneFlash(
          nextTitle
            ? t('home.sessionNextToast', { title: nextTitle })
            : t('home.sessionDoneToast'),
        );
      } else {
        navigation.navigate('Continue');
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.error'));
    } finally {
      setBusy(false);
    }
  };

  const onSkip = async () => {
    const action = project?.next_action;
    if (!action || busy) return;
    setBusy(true);
    setError(null);
    try {
      await skipAction(action.id);
      clearBlockRuntime(action.id);
      await refreshAfterMutation();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.error'));
    } finally {
      setBusy(false);
    }
  };

  const onToggleChecklist = async (
    itemId: string,
    nextDone: boolean,
  ) => {
    if (busy || !project?.next_action) return;
    setBusy(true);
    setError(null);
    try {
      await toggleChecklistItem(itemId, nextDone);
      setProject((prev) => {
        if (!prev?.next_action) return prev;
        return {
          ...prev,
          next_action: {
            ...prev.next_action,
            checklist_items: prev.next_action.checklist_items.map((item) =>
              item.id === itemId ? { ...item, done: nextDone } : item,
            ),
          },
          actions: prev.actions.map((action) =>
            action.id !== prev.next_action?.id
              ? action
              : {
                  ...action,
                  checklist_items: action.checklist_items.map((item) =>
                    item.id === itemId ? { ...item, done: nextDone } : item,
                  ),
                },
          ),
        };
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.error'));
    } finally {
      setBusy(false);
    }
  };

  const patchNextAction = (
    patch: Partial<NonNullable<ProjectDetail['next_action']>>,
  ) => {
    setProject((prev) => {
      if (!prev?.next_action) return prev;
      const next_action = { ...prev.next_action, ...patch };
      return {
        ...prev,
        next_action,
        actions: prev.actions.map((action) =>
          action.id === next_action.id ? { ...action, ...patch } : action,
        ),
      };
    });
  };

  const onCounterChange = async (nextCurrent: number) => {
    const action = project?.next_action;
    if (!action?.counter || busy) return;
    const previous = action.counter.current;
    patchNextAction({
      counter: { ...action.counter, current: nextCurrent },
    });
    setBusy(true);
    setError(null);
    try {
      const updated = await updateCounter(action.id, { current: nextCurrent });
      patchNextAction({
        counter: updated.counter,
        timers: updated.timers,
        timeline: updated.timeline,
        interval_plan: updated.interval_plan,
        stepper: updated.stepper,
      });
    } catch (e) {
      patchNextAction({
        counter: { ...action.counter, current: previous },
      });
      setError(e instanceof ApiError ? e.message : t('home.error'));
    } finally {
      setBusy(false);
    }
  };

  const onStepperBeatCounterChange = async (
    beatId: string,
    nextCurrent: number,
  ) => {
    const action = project?.next_action;
    if (!action?.stepper || busy) return;
    const previous = action.stepper;
    const optimisticBeats = previous.beats.map((beat) =>
      beat.id === beatId && beat.counter
        ? { ...beat, counter: { ...beat.counter, current: nextCurrent } }
        : beat,
    );
    patchNextAction({ stepper: { beats: optimisticBeats } });
    setBusy(true);
    setError(null);
    try {
      const updated = await updateStepperBeatCounter(action.id, beatId, {
        current: nextCurrent,
      });
      patchNextAction({
        stepper: updated.stepper,
        counter: updated.counter,
        timers: updated.timers,
        timeline: updated.timeline,
        interval_plan: updated.interval_plan,
      });
    } catch (e) {
      patchNextAction({ stepper: previous });
      setError(e instanceof ApiError ? e.message : t('home.error'));
    } finally {
      setBusy(false);
    }
  };

  const onCompleteTimer = async (timerId: string) => {
    const action = project?.next_action;
    if (!action) return;
    try {
      const updated = await completeTimer(action.id, timerId, true);
      patchNextAction({
        timers: updated.timers,
        counter: updated.counter,
        timeline: updated.timeline,
        interval_plan: updated.interval_plan,
        stepper: updated.stepper,
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.error'));
    }
  };

  const onOpenRepair = () => {
    if (busy) return;
    setError(null);
    setRepairSheetVisible(true);
  };

  const onPickRepairIntent = async (intent: RepairIntent) => {
    if (busy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError(null);
    setRepairSummary(null);
    try {
      const detail = await repairProject(
        projectId,
        { intent, reason: t('home.repairReason') },
        controller.signal,
      );
      setProject(detail);
      setRepairSheetVisible(false);
      if (detail.repair_summary) {
        setRepairSummary(detail.repair_summary);
      }
      const nextId = detail.next_action?.id ?? null;
      if (nextId) {
        shownActionIdRef.current = nextId;
        trackActionShown(projectId, nextId);
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof ApiError ? e.message : t('home.repairError'));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const onFinishCycle = async (partialNotes: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError(null);
    try {
      const detail = await completeCycle(
        projectId,
        { partial_notes: partialNotes || null },
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setProject(detail);
      setFinishCycleSheetVisible(false);
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(
        e instanceof ApiError ? e.message : t('home.finishCycleError'),
      );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const onStartNextCycle = async (comment: string) => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError(null);
    try {
      const detail = await startNextCycle(
        projectId,
        { comment: comment || null },
        controller.signal,
      );
      if (controller.signal.aborted) return;
      setProject(detail);
      setNextCycleSheetVisible(false);
      shownActionIdRef.current = null;
      const nextId = detail.next_action?.id ?? null;
      if (nextId) {
        shownActionIdRef.current = nextId;
        trackActionShown(projectId, nextId);
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(
        e instanceof ApiError ? e.message : t('home.nextCycleError'),
      );
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const next = project?.next_action ?? null;
  const peek = project?.peek_action ?? null;
  const peekDay = project?.peek_day ?? null;
  const currentDay = project?.current_day ?? null;
  const dayKind = currentDay?.kind ?? null;
  const isRestDay = dayKind === 'rest';
  const groupLabel = next?.group_title ?? null;
  // Waiting: today's executable work is done, but the plan continues
  // tomorrow — distinct from a fully finished project (docs/next/05).
  const waitingForNextDay =
    project != null &&
    project.status === 'active' &&
    next == null &&
    peek != null;
  const projectDone =
    project != null &&
    (project.status === 'completed' ||
      (next == null && peek == null));
  const cycleFinished =
    project?.next_cycle_available === true ||
    (project?.cycle_result != null && project.status === 'completed');
  const continueKind = project?.continue_kind ?? null;
  const unlockTiming = project?.next_unlock_date
    ? classifyUnlockDate(project.next_unlock_date)
    : null;

  const kindLabel = (kind: DayKind): string => {
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
  };

  const todayLead = (): string => {
    if (!dayKind) return t('home.today');
    switch (dayKind) {
      case 'rest':
        return t('home.restLead');
      case 'train':
        return t('home.trainLead');
      case 'cook_session':
        return t('home.cookLead');
      case 'other':
        return t('home.today');
      default: {
        const _exhaustive: never = dayKind;
        return _exhaustive;
      }
    }
  };

  if (loading && !project) {
    return (
      <SafeScreen>
        <AsyncState
          loading
          loadingMessage={t('home.loading')}
          retryLabel={t('projects.retry')}
          onRetry={() => void load()}
        >
          {null}
        </AsyncState>
      </SafeScreen>
    );
  }

  if (!project) {
    return (
      <SafeScreen>
        <AsyncState
          error={error ?? t('home.error')}
          retryLabel={t('projects.retry')}
          onRetry={() => void load()}
        >
          {null}
        </AsyncState>
      </SafeScreen>
    );
  }

  // Block Home on a loader until phase-3 plugins land (or fail).
  const pluginsPending =
    project.plugins_ready === false && !project.plugins_error;
  if (pluginsPending) {
    return (
      <SafeScreen>
        <AsyncState
          loading
          loadingMessage={t('home.pluginsLoading')}
          retryLabel={t('projects.retry')}
          onRetry={() => void load()}
        >
          {null}
        </AsyncState>
      </SafeScreen>
    );
  }

  if (project.plugins_ready === false && project.plugins_error) {
    return (
      <SafeScreen>
        <AsyncState
          error={error ?? t('home.pluginsError')}
          retryLabel={t('projects.retry')}
          onRetry={() => void onRetryPlugins()}
        >
          {null}
        </AsyncState>
      </SafeScreen>
    );
  }

  const isMultiDay = (currentDay?.horizon_days ?? 0) > 1;

  return (
    <>
      <SafeScreen scroll>
        {doneFlash ? (
          <View
            style={[
              styles.doneFlash,
              {
                backgroundColor: colors.surfaceMuted,
                borderColor: colors.border,
              },
            ]}
          >
            <Text
              style={[styles.doneFlashText, { color: colors.text }]}
              numberOfLines={2}
            >
              {doneFlash}
            </Text>
          </View>
        ) : null}

        {repairSummary ? (
          <View
            style={[
              styles.repairBanner,
              {
                backgroundColor: colors.surfaceMuted,
                borderColor: colors.border,
              },
            ]}
          >
            <Text style={[styles.repairBannerText, { color: colors.text }]}>
              {repairSummary}
            </Text>
            <Pressable onPress={() => setRepairSummary(null)} hitSlop={8}>
              <Text
                style={[styles.repairBannerClose, { color: colors.primary }]}
              >
                {t('common.dismiss')}
              </Text>
            </Pressable>
          </View>
        ) : null}

            {cycleFinished && project.cycle_result ? (
              <View style={styles.doneBlock}>
                <Text style={[styles.todayLabel, { color: colors.textMuted }]}>
                  {t('home.cycleDoneTitle')}
                </Text>
                {project.cycle_result.partial ? (
                  <Text
                    style={[styles.cyclePartial, { color: colors.textSecondary }]}
                  >
                    {t('home.cyclePartialBadge')}
                  </Text>
                ) : null}
                <Text style={[styles.doneTitle, { color: colors.text }]}>
                  {t('home.cycleResultDone', {
                    count: project.cycle_result.completed_steps,
                  })}
                </Text>
                <Text
                  style={[styles.waitingBody, { color: colors.textSecondary }]}
                >
                  {t('home.cycleResultSkipped', {
                    count: project.cycle_result.skipped_steps,
                  })}
                </Text>
                {project.cycle_result.partial_notes ? (
                  <Text
                    style={[styles.waitingBody, { color: colors.textSecondary }]}
                  >
                    {project.cycle_result.partial_notes}
                  </Text>
                ) : null}
                {(project.cycles_history?.length ?? 0) > 0 ? (
                  <Text
                    style={[styles.historyHint, { color: colors.textMuted }]}
                  >
                    {t('home.cycleHistoryLabel', {
                      n: project.cycles_history![
                        project.cycles_history!.length - 1
                      ].index,
                    })}
                  </Text>
                ) : project.cycle?.index ? (
                  <Text
                    style={[styles.historyHint, { color: colors.textMuted }]}
                  >
                    {t('home.cycleHistoryLabel', { n: project.cycle.index })}
                  </Text>
                ) : null}
                <PrimaryButton
                  label={
                    continueKind === 'repeat'
                      ? t('home.repeatCycle')
                      : t('home.nextCycle')
                  }
                  loading={busy}
                  onPress={() => setNextCycleSheetVisible(true)}
                  style={styles.cycleCta}
                />
              </View>
            ) : projectDone ? (
              <View style={styles.doneBlock}>
                <Text style={[styles.todayLabel, { color: colors.textMuted }]}>
                  {t('home.today')}
                </Text>
                <Text style={[styles.doneTitle, { color: colors.text }]}>
                  {t('home.allDone')}
                </Text>
              </View>
            ) : waitingForNextDay && peek ? (
              <View style={styles.doneBlock}>
                <Text style={[styles.todayLabel, { color: colors.textMuted }]}>
                  {t('home.today')}
                </Text>
                <Text style={[styles.doneTitle, { color: colors.text }]}>
                  {t('home.waitingTitle')}
                </Text>
                <Text
                  style={[styles.waitingBody, { color: colors.textSecondary }]}
                >
                  {unlockTiming === 'today'
                    ? t('home.opensToday')
                    : unlockTiming === 'tomorrow'
                      ? t('home.opensTomorrow')
                      : project?.next_unlock_date
                        ? t('home.opensOn', { date: project.next_unlock_date })
                        : t('home.opensLater')}
                </Text>
                <View
                  style={[
                    styles.peekCard,
                    {
                      backgroundColor: colors.surface,
                      borderColor: colors.border,
                    },
                  ]}
                >
                  <Text style={[styles.peekLabel, { color: colors.textMuted }]}>
                    {peekDay
                      ? t('home.dayOf', {
                          n: peekDay.day_number,
                          m: peekDay.horizon_days,
                          kind: kindLabel(peekDay.kind),
                        })
                      : t('home.peekLabel')}
                  </Text>
                  <Text style={[styles.peekTitle, { color: colors.text }]}>
                    {peek.title}
                  </Text>
                  {peek.why ? (
                    <Text
                      style={[styles.peekWhy, { color: colors.textSecondary }]}
                    >
                      {peek.why}
                    </Text>
                  ) : null}
                </View>
              </View>
            ) : next ? (
              <>
                {/* Slice D layout: title → day N/M → Full Block → detail / why */}
                <View style={styles.chrome}>
                  <Text style={[styles.stepTitle, { color: colors.text }]}>
                    {next.title}
                  </Text>
                  {isMultiDay && currentDay ? (
                    <Text
                      style={[styles.dayOf, { color: colors.textSecondary }]}
                    >
                      {t('home.dayOf', {
                        n: currentDay.day_number,
                        m: currentDay.horizon_days,
                        kind: kindLabel(currentDay.kind),
                      })}
                    </Text>
                  ) : null}
                  {next.estimate_min != null ? (
                    <Text
                      style={[styles.estimate, { color: colors.textSecondary }]}
                    >
                      {t('common.minutes', { count: next.estimate_min })}
                    </Text>
                  ) : null}
                </View>

                {isRestDay ? (
                  <View
                    style={[
                      styles.restStage,
                      {
                        borderColor: colors.border,
                        backgroundColor: colors.surfaceMuted,
                      },
                    ]}
                  >
                    <Text
                      style={[styles.todayLabel, { color: colors.textMuted }]}
                    >
                      {todayLead()}
                    </Text>
                    {currentDay?.title ? (
                      <Text style={[styles.restTitle, { color: colors.text }]}>
                        {currentDay.title}
                      </Text>
                    ) : null}
                    <Text
                      style={[styles.restHint, { color: colors.textSecondary }]}
                    >
                      {currentDay?.summary || t('home.restHint')}
                    </Text>
                  </View>
                ) : next.timeline ||
                  next.stepper ||
                  next.interval_plan ||
                  (next.timers?.length ?? 0) > 0 ||
                  next.counter ? (
                  <View style={styles.stage}>
                    {next.timeline ? (
                      <TimelineProgress
                        timeline={next.timeline}
                        interactive
                        disabled={busy}
                      />
                    ) : null}
                    {next.stepper ? (
                      <StepperPlayer
                        key={next.id}
                        actionId={next.id}
                        stepper={next.stepper}
                        interactive
                        disabled={busy}
                        onBeatCounterChange={(beatId, value) =>
                          void onStepperBeatCounterChange(beatId, value)
                        }
                      />
                    ) : null}
                    {next.interval_plan ? (
                      <IntervalPlayer
                        plan={next.interval_plan}
                        interactive
                        disabled={busy}
                      />
                    ) : null}
                    {!next.timeline &&
                    !next.stepper &&
                    !next.interval_plan &&
                    (next.timers?.length ?? 0) > 0 ? (
                      <TimerStack
                        timers={next.timers ?? []}
                        interactive
                        disabled={busy}
                        onCompleteTimer={(timerId) =>
                          void onCompleteTimer(timerId)
                        }
                      />
                    ) : null}
                    {!next.timeline &&
                    !next.stepper &&
                    !next.interval_plan &&
                    next.counter ? (
                      <CounterControl
                        counter={next.counter}
                        interactive
                        disabled={busy}
                        onChange={(value) => void onCounterChange(value)}
                      />
                    ) : null}
                  </View>
                ) : null}

                {next.detail ? (
                  <Text style={[styles.detail, { color: colors.textSecondary }]}>
                    {next.detail}
                  </Text>
                ) : null}

                {!isRestDay ? <WhyHero why={next.why} /> : null}
                {isRestDay && next.why ? (
                  <Text
                    style={[styles.restWhy, { color: colors.textSecondary }]}
                  >
                    {next.why}
                  </Text>
                ) : null}

                {groupLabel && !isRestDay ? (
                  <Text
                    style={[styles.groupLabel, { color: colors.textMuted }]}
                  >
                    {groupLabel}
                  </Text>
                ) : null}

                {next.checklist_items.length > 0 ? (
                  <View style={styles.checklist}>
                    <ChecklistList
                      items={next.checklist_items}
                      disabled={busy}
                      onToggle={(item, done) =>
                        void onToggleChecklist(item.id, done)
                      }
                    />
                  </View>
                ) : null}

                {(next.timeline || next.stepper || next.interval_plan) &&
                (next.timers?.length ?? 0) > 0 ? (
                  <View style={styles.plugins}>
                    <TimerStack
                      timers={next.timers ?? []}
                      interactive
                      disabled={busy}
                      onCompleteTimer={(timerId) =>
                        void onCompleteTimer(timerId)
                      }
                    />
                  </View>
                ) : null}

                {error ? (
                  <Text style={[styles.error, { color: colors.error }]}>
                    {error}
                  </Text>
                ) : null}

                {busy ? (
                  <View style={styles.busyRow}>
                    <ActivityIndicator color={colors.primary} />
                    <Text
                      style={[styles.busyText, { color: colors.textSecondary }]}
                    >
                      {t('home.working')}
                    </Text>
                    <Pressable
                      onPress={() => {
                        abortRef.current?.abort();
                        setBusy(false);
                      }}
                      hitSlop={8}
                    >
                      <Text style={{ color: colors.primary }}>
                        {t('common.cancel')}
                      </Text>
                    </Pressable>
                  </View>
                ) : null}

                <View style={styles.actions}>
                  <PrimaryButton
                    label={isRestDay ? t('home.doneRest') : t('home.done')}
                    loading={busy}
                    onPress={() => void onComplete()}
                    style={styles.actionBtn}
                  />
                  <PrimaryButton
                    variant="secondary"
                    label={t('home.skip')}
                    disabled={busy}
                    onPress={() => void onSkip()}
                    style={styles.actionBtn}
                  />
                </View>

              </>
            ) : null}

            {!projectDone && !cycleFinished ? (
              <PrimaryButton
                variant="ghost"
                label={t('home.repair')}
                disabled={busy}
                onPress={onOpenRepair}
                style={styles.pathBtn}
              />
            ) : null}

            {project?.can_finish_cycle && !cycleFinished ? (
              <PrimaryButton
                variant="ghost"
                label={t('home.finishCycle')}
                disabled={busy}
                onPress={() => setFinishCycleSheetVisible(true)}
                style={styles.pathBtn}
              />
            ) : null}
          </SafeScreen>

      <RepairSheet
        visible={repairSheetVisible}
        busy={busy}
        onPick={(intent) => void onPickRepairIntent(intent)}
        onClose={() => setRepairSheetVisible(false)}
      />

      <FinishCycleSheet
        visible={finishCycleSheetVisible}
        busy={busy}
        onConfirm={(notes) => void onFinishCycle(notes)}
        onClose={() => setFinishCycleSheetVisible(false)}
      />

      <NextCycleSheet
        visible={nextCycleSheetVisible}
        busy={busy}
        continueKind={continueKind ?? 'next'}
        continueLabel={project?.continue_label}
        onConfirm={(comment) => void onStartNextCycle(comment)}
        onClose={() => setNextCycleSheetVisible(false)}
      />
    </>
  );
}

const styles = StyleSheet.create({
  chrome: {
    marginBottom: spacing.md,
    gap: spacing.xs,
  },
  dayOf: {
    ...typography.caption,
  },
  todayLabel: {
    ...typography.label,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  restHint: {
    ...typography.body,
    marginBottom: spacing.sm,
  },
  restTitle: {
    ...typography.subtitle,
    marginBottom: spacing.xs,
  },
  restWhy: {
    ...typography.body,
    marginTop: spacing.md,
  },
  groupLabel: {
    ...typography.caption,
    marginTop: spacing.sm,
  },
  stepTitle: {
    ...typography.hero,
  },
  estimate: {
    ...typography.caption,
  },
  checklist: {
    marginTop: spacing.lg,
  },
  plugins: {
    marginTop: spacing.lg,
  },
  stage: {
    marginBottom: spacing.lg,
    minHeight: 320,
    gap: spacing.md,
  },
  restStage: {
    borderWidth: 1,
    borderRadius: radii.lg,
    padding: spacing.lg,
    marginBottom: spacing.lg,
    gap: spacing.sm,
    minHeight: 160,
  },
  detail: {
    ...typography.body,
    marginTop: spacing.md,
  },
  error: {
    ...typography.caption,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  busyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  busyText: {
    ...typography.caption,
    flex: 1,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xl,
  },
  actionBtn: {
    flex: 1,
  },
  pathBtn: {
    marginTop: spacing.lg,
  },
  doneBlock: {
    marginBottom: spacing.md,
  },
  doneTitle: {
    ...typography.title,
  },
  cyclePartial: {
    ...typography.caption,
    marginBottom: spacing.xs,
  },
  historyHint: {
    ...typography.caption,
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  cycleCta: {
    marginTop: spacing.md,
  },
  waitingBody: {
    ...typography.body,
    marginTop: spacing.xs,
  },
  peekCard: {
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    marginTop: spacing.lg,
    opacity: 0.85,
  },
  peekLabel: {
    ...typography.label,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  peekTitle: {
    ...typography.subtitle,
  },
  peekWhy: {
    ...typography.body,
    marginTop: spacing.xs,
  },
  doneFlash: {
    borderWidth: 1,
    borderRadius: radii.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
  },
  doneFlashText: {
    ...typography.body,
  },
  repairBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.sm,
    marginBottom: spacing.lg,
  },
  repairBannerText: {
    ...typography.body,
    flex: 1,
  },
  repairBannerClose: {
    ...typography.caption,
  },
});
