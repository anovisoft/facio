import React, {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import { Alert, Pressable, StyleSheet, Text, View } from 'react-native';
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
import {
  abandonProject,
  completeCycle,
  getProject,
  postponeDay,
  rematerializePlugins,
  restoreState,
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
import { goBackOrContinue, resetToContinue } from '@/navigation/reliableBack';
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

/** Earlier same-day Session peer (browse Back — no uncomplete). */
function earlierSameDayPeer(
  actions: ActionResponse[],
  current: ActionResponse,
): ActionResponse | null {
  const day = sameDayActions(actions, current.day_offset);
  const idx = day.findIndex((a) => a.id === current.id);
  if (idx <= 0) return null;
  return day[idx - 1] ?? null;
}

/** Later same-day Session peer (browse Next — no complete). */
function laterSameDayPeer(
  actions: ActionResponse[],
  current: ActionResponse,
): ActionResponse | null {
  const day = sameDayActions(actions, current.day_offset);
  const idx = day.findIndex((a) => a.id === current.id);
  if (idx < 0 || idx >= day.length - 1) return null;
  return day[idx + 1] ?? null;
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
  /** Same-day browse peek — null follows live `next_action`. */
  const [browseActionId, setBrowseActionId] = useState<string | null>(null);
  /** Manual / repair Undo target (state_version). */
  const [undoVersion, setUndoVersion] = useState<number | null>(null);
  const [undoMessage, setUndoMessage] = useState<string | null>(null);
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

  // After a real complete, follow the new live next (drop browse peek).
  useEffect(() => {
    setBrowseActionId(null);
  }, [project?.next_action?.id]);

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
      const pendingUndo = route.params.undoVersion;
      if (pendingUndo != null) {
        setUndoVersion(pendingUndo);
        setUndoMessage(route.params.undoMessage ?? t('manualEdit.applied'));
        navigation.setParams({
          undoVersion: undefined,
          undoMessage: undefined,
        });
      }
      return () => abortRef.current?.abort();
    }, [
      load,
      navigation,
      route.params.undoMessage,
      route.params.undoVersion,
      t,
    ]),
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
    setBrowseActionId(null);
    const detail = await refreshAfterMutation();
    // Done (daily / last same-day / assurance) → Continue; else toast + stay.
    if (!opts.preferContinue && detail.next_action) {
      const nextTitle = detail.next_action.title?.trim();
      showDoneFlash(
        nextTitle
          ? t('home.sessionNextToast', { title: nextTitle })
          : t('home.sessionDoneToast'),
      );
    } else {
      resetToContinue(navigation);
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

  const onDone = () => {
    // Live next_action only — assurance complete. Last same-day / daily →
    // Continue; intermediate same-day → stay on the new live next.
    const p = projectRef.current;
    if (!p?.next_action) return;
    const action = p.next_action;
    const horizon =
      p.current_day?.horizon_days ?? p.cycle?.horizon_days ?? 1;
    let preferContinue = true;
    if (horizon <= 1) {
      const peers = sameDayActions(p.actions, action.day_offset);
      const pending = peers.filter((a) => a.status === 'pending');
      const isLast =
        pending.length === 1 && pending[0]?.id === action.id;
      preferContinue = isLast;
    }
    void runComplete({ preferContinue, withAssurance: true });
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
        resetToContinue(navigation);
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
      resetToContinue(navigation);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('home.postponeError'));
    } finally {
      setBusy(false);
    }
  };

  const onUndoManual = async () => {
    if (busy || undoVersion == null) return;
    setBusy(true);
    setError(null);
    try {
      const detail = await restoreState(projectId, undoVersion);
      setProject(detail);
      setUndoVersion(null);
      setUndoMessage(null);
      setBrowseActionId(null);
    } catch (e) {
      setError(
        e instanceof ApiError ? e.message : t('manualEdit.undoError'),
      );
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
                resetToContinue(navigation);
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
    const horizon =
      project?.current_day?.horizon_days ??
      project?.cycle?.horizon_days ??
      1;
    const isDaily = horizon > 1;
    const canFinish = project?.can_finish_cycle === true;

    // Native iOS compact alert (UIAlertController) — same as first kebab ship.
    const buttons: {
      text: string;
      style?: 'cancel' | 'destructive' | 'default';
      onPress?: () => void;
    }[] = [
      { text: t('home.fullGuide'), onPress: openGuide },
      {
        text: t('home.editSession'),
        onPress: () => {
          const live =
            browseActionId != null
              ? project?.actions.find((a) => a.id === browseActionId)
              : project?.next_action;
          const actionKey = live?.key ?? project?.next_action?.key ?? null;
          navigation.navigate('ManualEdit', {
            projectId,
            mode: 'active',
            actionKey,
          });
        },
      },
    ];
    if (isDaily) {
      buttons.push({
        text: t('home.postponeTomorrow'),
        onPress: () => {
          void onPostpone();
        },
      });
    }
    buttons.push({
      text: t('home.skip'),
      onPress: () => {
        void onSkip();
      },
    });
    if (canFinish) {
      buttons.push({
        text: t('home.finishCycle'),
        onPress: () => setFinishCycleSheetVisible(true),
      });
    }
    buttons.push({
      text: t('home.archive'),
      style: 'destructive',
      onPress: onArchive,
    });
    buttons.push({ text: t('common.cancel'), style: 'cancel' });
    Alert.alert(t('home.menuPath'), undefined, buttons);
  };

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
    project?.next_action?.key,
    project?.actions,
    browseActionId,
    projectId,
    busy,
    t,
    colors.text,
  ]);

  const onToggleChecklist = async (
    itemId: string,
    nextDone: boolean,
  ) => {
    // Browse peek is read-only — only the live next_action can toggle.
    if (!project?.next_action || busy) return;
    if (
      browseActionId != null &&
      browseActionId !== project.next_action.id
    ) {
      return;
    }
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
  const displayed =
    browseActionId != null
      ? (project?.actions.find((a) => a.id === browseActionId) ?? next)
      : next;
  const sessionLive =
    displayed != null && next != null && displayed.id === next.id;
  const openManualEditFor = (action: ActionResponse | null | undefined) => {
    const actionKey =
      action?.key?.trim() || project?.next_action?.key?.trim() || null;
    navigation.navigate('ManualEdit', {
      projectId,
      mode: 'active',
      actionKey,
    });
  };
  const onBrowseNext = () => {
    const action = displayed;
    if (!project || !action || busy) return;
    const later = laterSameDayPeer(project.actions, action);
    if (!later) return;
    // Landing on live next clears browse; otherwise peek ahead.
    if (later.id === project.next_action?.id) {
      setBrowseActionId(null);
    } else {
      setBrowseActionId(later.id);
    }
  };
  const onBrowseBack = () => {
    const action = displayed;
    if (!project || !action || busy) return;
    const earlier = earlierSameDayPeer(project.actions, action);
    if (!earlier) return;
    setBrowseActionId(earlier.id);
  };
  const peek = project?.peek_action ?? null;
  const peekDay = project?.peek_day ?? null;
  const currentDay = project?.current_day ?? null;
  const dayKind = currentDay?.kind ?? null;
  const isRestDay = dayKind === 'rest';
  const groupLabel = displayed?.group_title ?? null;
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
  const canBrowseBack =
    displayed != null &&
    earlierSameDayPeer(project.actions, displayed) != null;
  const canBrowseNext =
    displayed != null &&
    laterSameDayPeer(project.actions, displayed) != null;
  const showSessionFooter =
    next != null && !projectDone && !cycleFinished;

  const sameDayBrowseRow = (
    <View style={styles.footerRow}>
      <PrimaryButton
        variant="secondary"
        label={t('home.back')}
        disabled={busy || !canBrowseBack}
        onPress={onBrowseBack}
        style={styles.actionBtn}
      />
      <PrimaryButton
        variant="secondary"
        label={t('home.next')}
        disabled={busy || !canBrowseNext}
        onPress={onBrowseNext}
        style={styles.actionBtn}
      />
    </View>
  );

  const stickyFooter = showSessionFooter ? (
    isSameDayPlan ? (
      sessionLive && isLastSameDayStep ? (
        <View style={styles.footerRow}>
          <PrimaryButton
            variant="secondary"
            label={t('home.back')}
            disabled={busy || !canBrowseBack}
            onPress={onBrowseBack}
            style={styles.actionBtn}
          />
          <PrimaryButton
            label={isRestDay ? t('home.doneRest') : t('home.done')}
            loading={busy}
            onPress={onDone}
            style={styles.actionBtn}
          />
        </View>
      ) : sessionLive ? (
        <View style={styles.footerColumn}>
          <PrimaryButton
            label={isRestDay ? t('home.doneRest') : t('home.done')}
            loading={busy}
            onPress={onDone}
          />
          {sameDayBrowseRow}
        </View>
      ) : (
        sameDayBrowseRow
      )
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

        {undoVersion != null ? (
          <View
            style={[
              styles.undoBanner,
              {
                backgroundColor: colors.surfaceMuted,
                borderColor: colors.border,
              },
            ]}
          >
            <Text
              style={[styles.undoBannerText, { color: colors.text }]}
              numberOfLines={2}
            >
              {undoMessage ?? t('manualEdit.applied')}
            </Text>
            <Pressable
              onPress={() => void onUndoManual()}
              disabled={busy}
              hitSlop={8}
            >
              <Text style={[styles.undoBannerAction, { color: colors.primary }]}>
                {t('manualEdit.undo')}
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
            ) : displayed ? (
              <>
                {/* Slice D layout: title → day N/M → Full Block → detail / why */}
                <View style={styles.chrome}>
                  <Text style={[styles.stepTitle, { color: colors.text }]}>
                    {displayed.title}
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
                  {displayed.estimate_min != null ? (
                    <Text
                      style={[styles.estimate, { color: colors.textSecondary }]}
                    >
                      {t('common.minutes', { count: displayed.estimate_min })}
                    </Text>
                  ) : null}
                  {!sessionLive ? (
                    <Text
                      style={[styles.browseHint, { color: colors.textMuted }]}
                    >
                      {t('home.browseHint')}
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
                ) : displayed.timeline ||
                  displayed.stepper ||
                  displayed.interval_plan ||
                  (displayed.timers?.length ?? 0) > 0 ||
                  displayed.counter ? (
                  <View style={styles.stage}>
                    {displayed.timeline ? (
                      <TimelineProgress
                        timeline={displayed.timeline}
                        interactive={sessionLive}
                        disabled={busy || !sessionLive}
                      />
                    ) : null}
                    {displayed.stepper ? (
                      <StepperPlayer
                        key={displayed.id}
                        actionId={displayed.id}
                        stepper={displayed.stepper}
                        interactive={sessionLive}
                        disabled={busy || !sessionLive}
                        onEdit={() => openManualEditFor(displayed)}
                        onBeatCounterChange={(beatId, value) =>
                          void onStepperBeatCounterChange(beatId, value)
                        }
                      />
                    ) : null}
                    {displayed.interval_plan ? (
                      <IntervalPlayer
                        plan={displayed.interval_plan}
                        interactive={sessionLive}
                        disabled={busy || !sessionLive}
                      />
                    ) : null}
                    {!displayed.timeline &&
                    !displayed.stepper &&
                    !displayed.interval_plan &&
                    (displayed.timers?.length ?? 0) > 0 ? (
                      <TimerStack
                        timers={displayed.timers ?? []}
                        interactive={sessionLive}
                        disabled={busy || !sessionLive}
                        onCompleteTimer={(timerId) =>
                          void onCompleteTimer(timerId)
                        }
                      />
                    ) : null}
                    {!displayed.timeline &&
                    !displayed.stepper &&
                    !displayed.interval_plan &&
                    displayed.counter ? (
                      <CounterControl
                        counter={displayed.counter}
                        interactive={sessionLive}
                        disabled={busy || !sessionLive}
                        onEdit={() => openManualEditFor(displayed)}
                        onChange={(value) => void onCounterChange(value)}
                      />
                    ) : null}
                  </View>
                ) : null}

                {displayed.detail ? (
                  <Text style={[styles.detail, { color: colors.textSecondary }]}>
                    {displayed.detail}
                  </Text>
                ) : null}

                {!isRestDay ? <WhyHero why={displayed.why} /> : null}
                {isRestDay && displayed.why ? (
                  <Text
                    style={[styles.restWhy, { color: colors.textSecondary }]}
                  >
                    {displayed.why}
                  </Text>
                ) : null}

                {groupLabel && !isRestDay ? (
                  <Text
                    style={[styles.groupLabel, { color: colors.textMuted }]}
                  >
                    {groupLabel}
                  </Text>
                ) : null}

                {displayed.checklist_items.length > 0 ? (
                  <View style={styles.checklist}>
                    <ChecklistList
                      items={displayed.checklist_items}
                      disabled={busy || !sessionLive}
                      onEdit={() => openManualEditFor(displayed)}
                      onToggle={
                        sessionLive
                          ? (item, done) =>
                              void onToggleChecklist(item.id, done)
                          : undefined
                      }
                    />
                  </View>
                ) : null}

                {(displayed.timeline ||
                  displayed.stepper ||
                  displayed.interval_plan) &&
                (displayed.timers?.length ?? 0) > 0 ? (
                  <View style={styles.plugins}>
                    <TimerStack
                      timers={displayed.timers ?? []}
                      interactive={sessionLive}
                      disabled={busy || !sessionLive}
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
  footerColumn: {
    gap: spacing.sm,
  },
  actionBtn: {
    flex: 1,
  },
  browseHint: {
    ...typography.caption,
    marginTop: spacing.xs,
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
  undoBanner: {
    borderWidth: 1,
    borderRadius: radii.md,
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.md,
    marginBottom: spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  undoBannerText: {
    ...typography.body,
    flex: 1,
  },
  undoBannerAction: {
    ...typography.label,
    fontWeight: '700',
  },
});
