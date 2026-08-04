import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import {
  completeAction,
  completeTimer,
  skipAction,
  toggleChecklistItem,
  uncompleteAction,
  updateCounter,
  updateStepperBeatCounter,
} from '@/api/actions';
import {
  abandonProject,
  completeCycle,
  getProject,
  postponeDay,
  rematerializePlugins,
  startNextCycle,
} from '@/api/projects';
import {
  ApiError,
  type ActionResponse,
  type DayKind,
  type ProjectDetail,
} from '@/api/types';
import { FinishCycleSheet } from '@/features/home/FinishCycleSheet';
import { NextCycleSheet } from '@/features/home/NextCycleSheet';
import {
  SessionMenuSheet,
  type SessionMenuAction,
} from '@/features/home/SessionMenuSheet';
import { goBackOrContinue } from '@/navigation/reliableBack';
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

function sameDayActions(
  actions: ActionResponse[],
  dayOffset: number | null | undefined,
): ActionResponse[] {
  const day = dayOffset ?? 0;
  return actions.filter((a) => (a.day_offset ?? 0) === day);
}

function previousClosedSameDay(
  actions: ActionResponse[],
  current: ActionResponse,
): ActionResponse | null {
  const day = sameDayActions(actions, current.day_offset);
  const idx = day.findIndex((a) => a.id === current.id);
  if (idx <= 0) return null;
  for (let i = idx - 1; i >= 0; i -= 1) {
    const a = day[i];
    if (a.status === 'done' || a.status === 'skipped') return a;
  }
  return null;
}

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
  const [nextCycleSheetVisible, setNextCycleSheetVisible] = useState(false);
  const [finishCycleSheetVisible, setFinishCycleSheetVisible] = useState(false);
  const [sessionMenuVisible, setSessionMenuVisible] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const shownActionIdRef = useRef<string | null>(null);
  const doneFlashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const projectRef = useRef<ProjectDetail | null>(null);
  projectRef.current = project;

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

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    // Cold load only — keep Session layout stable on focus refresh (P3).
    if (projectRef.current == null) setLoading(true);
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

  const finishAction = async (
    actionId: string,
    opts: { preferContinue: boolean },
  ) => {
    await completeAction(actionId);
    clearBlockRuntime(actionId);
    const detail = await refreshAfterMutation();
    // Last Done / daily Done → Continue; intermediate Next → toast + stay.
    if (!opts.preferContinue && detail.next_action) {
      const nextTitle = detail.next_action.title?.trim();
      showDoneFlash(
        nextTitle
          ? t('home.sessionNextToast', { title: nextTitle })
          : t('home.sessionDoneToast'),
      );
    } else {
      navigation.navigate('Continue');
    }
  };

  const markRemainingAndComplete = async (
    action: ActionResponse,
    opts: { preferContinue: boolean },
  ) => {
    const incomplete = action.checklist_items.filter((i) => !i.done);
    if (incomplete.length > 0) {
      await Promise.all(
        incomplete.map((item) => toggleChecklistItem(item.id, true)),
      );
      setProject((prev) => {
        if (!prev?.next_action) return prev;
        const markDone = (
          items: typeof prev.next_action.checklist_items,
        ) =>
          items.map((item) =>
            incomplete.some((u) => u.id === item.id)
              ? { ...item, done: true }
              : item,
          );
        return {
          ...prev,
          next_action: {
            ...prev.next_action,
            checklist_items: markDone(prev.next_action.checklist_items),
          },
          actions: prev.actions.map((a) =>
            a.id !== prev.next_action?.id
              ? a
              : {
                  ...a,
                  checklist_items: markDone(a.checklist_items),
                },
          ),
        };
      });
    }
    await finishAction(action.id, opts);
  };

  const runComplete = async (opts: {
    preferContinue: boolean;
    withAssurance: boolean;
  }) => {
    if (!project?.next_action || busy) return;
    const action = project.next_action;
    const incomplete = action.checklist_items.filter((i) => !i.done);

    const execute = () => {
      void (async () => {
        if (busy) return;
        setBusy(true);
        setError(null);
        try {
          await markRemainingAndComplete(action, {
            preferContinue: opts.preferContinue,
          });
        } catch (e) {
          setError(e instanceof ApiError ? e.message : t('home.error'));
        } finally {
          setBusy(false);
        }
      })();
    };

    if (!opts.withAssurance) {
      execute();
      return;
    }

    if (incomplete.length > 0) {
      Alert.alert(
        t('home.checklistConfirmTitle'),
        t('home.checklistConfirmMessage', { count: incomplete.length }),
        [
          { text: t('common.cancel'), style: 'cancel' },
          { text: t('home.checklistConfirmYes'), onPress: execute },
        ],
      );
      return;
    }

    Alert.alert(t('home.finishConfirmTitle'), t('home.finishConfirmMessage'), [
      { text: t('common.cancel'), style: 'cancel' },
      { text: t('home.finishConfirmYes'), onPress: execute },
    ]);
  };

  const onNext = () => {
    // Intermediate same-day: complete → next Session; no modal.
    void runComplete({ preferContinue: false, withAssurance: false });
  };

  const onDone = () => {
    // Daily Done + last same-day step: always-on assurance modal.
    void runComplete({ preferContinue: true, withAssurance: true });
  };

  const onBack = async () => {
    const action = project?.next_action;
    if (!action || busy) return;
    const prev = previousClosedSameDay(project.actions, action);
    if (!prev) return;
    setBusy(true);
    setError(null);
    try {
      await uncompleteAction(prev.id);
      clearBlockRuntime(prev.id);
      await refreshAfterMutation();
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
      const detail = await refreshAfterMutation();
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

  const onPostpone = async () => {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const detail = await postponeDay(projectId);
      setProject(detail);
      navigation.navigate('Continue');
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.postponeError'));
    } finally {
      setBusy(false);
    }
  };

  const onArchive = () => {
    Alert.alert(
      t('home.archiveConfirmTitle'),
      t('home.archiveConfirmMessage'),
      [
        { text: t('common.cancel'), style: 'cancel' },
        {
          text: t('home.archiveConfirmYes'),
          style: 'destructive',
          onPress: () => {
            void (async () => {
              if (busy) return;
              setBusy(true);
              setError(null);
              try {
                await abandonProject(projectId);
                navigation.navigate('Continue');
              } catch (e) {
                setError(
                  e instanceof ApiError ? e.message : t('home.archiveError'),
                );
              } finally {
                setBusy(false);
              }
            })();
          },
        },
      ],
    );
  };

  const openSessionMenu = () => {
    if (busy) return;
    setSessionMenuVisible(true);
  };

  const onSessionMenuAction = (action: SessionMenuAction) => {
    switch (action) {
      case 'fullGuide':
        openGuide();
        break;
      case 'editSession':
        Alert.alert(t('home.editSession'), t('home.editSessionSoon'));
        break;
      case 'postpone':
        void onPostpone();
        break;
      case 'skip':
        void onSkip();
        break;
      case 'finishCycle':
        setFinishCycleSheetVisible(true);
        break;
      case 'archive':
        onArchive();
        break;
      default: {
        const _exhaustive: never = action;
        return _exhaustive;
      }
    }
  };

  const sessionHorizon =
    project?.current_day?.horizon_days ?? project?.cycle?.horizon_days ?? 1;
  const sessionMenuIsDaily = sessionHorizon > 1;
  const sessionMenuCanFinish = project?.can_finish_cycle === true;

  useLayoutEffect(() => {
    const title =
      project?.title ||
      project?.outcome ||
      project?.paraphrase ||
      t('home.today');

    // Icon-only chips in stack header: iOS 26 supplies one system liquid-glass
    // capsule. Do NOT use unstable_header*Items type button/menu — our
    // react-native-screens@4.16 does not render those bar-button items (buttons
    // vanish). Custom bordered chips + system glass = double outline.
    navigation.setOptions({
      title,
      headerBackButtonDisplayMode: 'minimal',
      headerBackTitle: '',
      // Clear any previous unstable items from earlier dogfood builds.
      unstable_headerLeftItems: undefined,
      unstable_headerRightItems: undefined,
      headerLeft: () => (
        <View style={styles.headerNavSlot}>
          <GlassIconButton
            variant="header"
            onPress={() => goBackOrContinue(navigation)}
            accessibilityLabel={t('home.back')}
            size={GLASS_ICON_CHIP_SIZE}
          >
            <Ionicons name="chevron-back" size={22} color={colors.text} />
          </GlassIconButton>
        </View>
      ),
      headerRight: () => (
        <View style={styles.headerNavSlot}>
          <GlassIconButton
            variant="header"
            onPress={openSessionMenu}
            accessibilityLabel={t('home.menuPath')}
            size={GLASS_ICON_CHIP_SIZE}
          >
            <Ionicons name="ellipsis-vertical" size={22} color={colors.text} />
          </GlassIconButton>
        </View>
      ),
    });
  }, [
    navigation,
    project?.title,
    project?.outcome,
    project?.paraphrase,
    busy,
    t,
    colors.text,
  ]);

  const onToggleChecklist = async (
    itemId: string,
    nextDone: boolean,
  ) => {
    if (!project?.next_action || busy) return;
    const previousDone = project.next_action.checklist_items.find(
      (i) => i.id === itemId,
    )?.done;
    // Optimistic — no global busy / layout jump (P3).
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
    setError(null);
    try {
      await toggleChecklistItem(itemId, nextDone);
    } catch (e) {
      if (previousDone !== undefined) {
        setProject((prev) => {
          if (!prev?.next_action) return prev;
          return {
            ...prev,
            next_action: {
              ...prev.next_action,
              checklist_items: prev.next_action.checklist_items.map((item) =>
                item.id === itemId ? { ...item, done: previousDone } : item,
              ),
            },
            actions: prev.actions.map((action) =>
              action.id !== prev.next_action?.id
                ? action
                : {
                    ...action,
                    checklist_items: action.checklist_items.map((item) =>
                      item.id === itemId
                        ? { ...item, done: previousDone }
                        : item,
                    ),
                  },
            ),
          };
        });
      }
      setError(e instanceof ApiError ? e.message : t('home.error'));
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

  const horizonDays =
    currentDay?.horizon_days ?? project.cycle?.horizon_days ?? 1;
  const isSameDayPlan = horizonDays <= 1;
  const isMultiDay = horizonDays > 1;
  const dayPeers = next
    ? sameDayActions(project.actions, next.day_offset)
    : [];
  const pendingSameDay = dayPeers.filter((a) => a.status === 'pending');
  const isLastSameDayStep =
    next != null &&
    pendingSameDay.length === 1 &&
    pendingSameDay[0]?.id === next.id;
  const canGoBackSession =
    next != null && previousClosedSameDay(project.actions, next) != null;
  const showSessionFooter =
    next != null && !projectDone && !cycleFinished;

  const stickyFooter = showSessionFooter ? (
    isSameDayPlan ? (
      <View style={styles.footerRow}>
        <PrimaryButton
          variant="secondary"
          label={t('home.back')}
          disabled={busy || !canGoBackSession}
          onPress={() => void onBack()}
          style={styles.actionBtn}
        />
        <PrimaryButton
          label={
            isLastSameDayStep
              ? isRestDay
                ? t('home.doneRest')
                : t('home.done')
              : t('home.next')
          }
          loading={busy}
          onPress={isLastSameDayStep ? onDone : onNext}
          style={styles.actionBtn}
        />
      </View>
    ) : (
      <PrimaryButton
        label={isRestDay ? t('home.doneRest') : t('home.done')}
        loading={busy}
        onPress={onDone}
      />
    )
  ) : null;

  return (
    <>
      <SafeScreen scroll footer={stickyFooter}>
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
              </>
            ) : null}

            {!next && error ? (
              <Text style={[styles.error, { color: colors.error }]}>
                {error}
              </Text>
            ) : null}
          </SafeScreen>

      <SessionMenuSheet
        visible={sessionMenuVisible}
        isDaily={sessionMenuIsDaily}
        canFinish={sessionMenuCanFinish}
        onAction={onSessionMenuAction}
        onClose={() => setSessionMenuVisible(false)}
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
  headerNavSlot: {
    width: GLASS_ICON_CHIP_SIZE,
    height: GLASS_ICON_CHIP_SIZE,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
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
  footerRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  actionBtn: {
    flex: 1,
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
});
