import React, {
  useCallback,
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
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import {
  completeAction,
  skipAction,
  toggleChecklistItem,
} from '@/api/actions';
import { getProject, repairProject } from '@/api/projects';
import { ApiError, type ProjectDetail } from '@/api/types';
import { FirstCompletionOverlay } from '@/features/home/FirstCompletionOverlay';
import type { RootScreenProps } from '@/navigation/types';
import { trackActionShown } from '@/services/beacons';
import { AsyncState } from '@/shared/ui/AsyncState';
import { ChecklistList } from '@/shared/ui/ChecklistList';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { WhyHero } from '@/shared/ui/WhyHero';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

export function ProjectHomeScreen({
  navigation,
  route,
}: RootScreenProps<'ProjectHome'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId } = route.params;
  const markFirstCompletionShown = useSessionStore(
    (s) => s.markFirstCompletionShown,
  );
  const hasFirstCompletionShown = useSessionStore((s) =>
    s.hasFirstCompletionShown(projectId),
  );

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFirstCompletion, setShowFirstCompletion] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const shownActionIdRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    navigation.setOptions({
      title: project?.title || project?.outcome || project?.paraphrase || t('home.today'),
    });
  }, [navigation, project?.title, project?.outcome, project?.paraphrase, t]);

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

    const isFirstDone =
      !hasFirstCompletionShown &&
      project.actions.every((a) => a.status !== 'done');

    setBusy(true);
    setError(null);
    try {
      await completeAction(action.id);
      await refreshAfterMutation();
      if (isFirstDone) {
        markFirstCompletionShown(projectId);
        setShowFirstCompletion(true);
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

  const onRepair = async () => {
    if (busy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setBusy(true);
    setError(null);
    try {
      const detail = await repairProject(
        projectId,
        t('home.repairReason'),
        controller.signal,
      );
      setProject(detail);
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

  const next = project?.next_action ?? null;
  const groupLabel = next?.group_title ?? null;
  const projectDone =
    project != null &&
    (project.status === 'completed' || next == null);

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

  return (
    <>
      <SafeScreen scroll>
        {projectDone ? (
          <View style={styles.doneBlock}>
            <Text style={[styles.todayLabel, { color: colors.textMuted }]}>
              {t('home.today')}
            </Text>
            <Text style={[styles.doneTitle, { color: colors.text }]}>
              {t('home.allDone')}
            </Text>
          </View>
        ) : next ? (
          <>
            <Text style={[styles.todayLabel, { color: colors.textMuted }]}>
              {t('home.today')}
            </Text>
            {groupLabel ? (
              <Text style={[styles.groupLabel, { color: colors.textMuted }]}>
                {groupLabel}
              </Text>
            ) : null}
            <Text style={[styles.stepTitle, { color: colors.text }]}>
              {next.title}
            </Text>
            {next.estimate_min != null ? (
              <Text style={[styles.estimate, { color: colors.textSecondary }]}>
                {t('common.minutes', { count: next.estimate_min })}
              </Text>
            ) : null}

            <WhyHero why={next.why} />

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
                label={t('home.done')}
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

        <PrimaryButton
          variant="ghost"
          label={t('home.fullPath')}
          disabled={busy}
          onPress={() => navigation.navigate('Path', { projectId })}
          style={styles.pathBtn}
        />

        {!projectDone ? (
          <PrimaryButton
            variant="ghost"
            label={t('home.repair')}
            disabled={busy}
            onPress={() => void onRepair()}
          />
        ) : null}
      </SafeScreen>

      <FirstCompletionOverlay
        visible={showFirstCompletion}
        onContinue={() => setShowFirstCompletion(false)}
      />
    </>
  );
}

const styles = StyleSheet.create({
  todayLabel: {
    ...typography.label,
    textTransform: 'uppercase',
    marginBottom: spacing.xs,
  },
  groupLabel: {
    ...typography.caption,
    marginBottom: spacing.xs,
  },
  stepTitle: {
    ...typography.hero,
    marginBottom: spacing.xs,
  },
  estimate: {
    ...typography.caption,
  },
  checklist: {
    marginTop: spacing.lg,
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
});
