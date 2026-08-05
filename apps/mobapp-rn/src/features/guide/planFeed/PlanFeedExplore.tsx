import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTranslation } from 'react-i18next';

import { ApiError, type ProjectDetail } from '@/api/types';
import {
  commitProject,
  getProject,
  refineProject,
  restoreState,
} from '@/api/projects';
import { PlanFeedPlanCard } from '@/features/guide/planFeed/PlanFeedPlanCard';
import { PlanFeedQuestions } from '@/features/guide/planFeed/PlanFeedQuestions';
import { isPathReady } from '@/features/guide/planFeed/snapshot';
import type { PlanSnapshot } from '@/features/guide/planFeed/types';
import { usePlanFeed } from '@/features/guide/planFeed/usePlanFeed';
import type { RootScreenProps } from '@/navigation/types';
import { trackAcceptViewed } from '@/services/beacons';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const PATH_POLL_MS = 1500;

function abortError(): Error {
  const err = new Error('Aborted');
  err.name = 'AbortError';
  return err;
}

function isAbortError(e: unknown): boolean {
  return e instanceof Error && e.name === 'AbortError';
}

type CommitIntent = 'start' | 'save';

type Props = {
  navigation:
    | RootScreenProps<'Guide'>['navigation']
    | RootScreenProps<'GuideExplore'>['navigation'];
  projectId: string;
  project: ProjectDetail;
  setProject: (detail: ProjectDetail) => void;
  error: string | null;
  setError: (msg: string | null) => void;
};

/**
 * Create Plan Feed (Slice E2a) — versioned лента for pre-Commitment Explore.
 * Start Guide lives on each plan card; no sticky page-bottom Start.
 */
export function PlanFeedExplore({
  navigation,
  projectId,
  project,
  setProject,
  error,
  setError,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const clearPlanFeed = useSessionStore((s) => s.clearPlanFeed);
  const { items, appendUserTurn, syncFromProject } = usePlanFeed(projectId);

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [queuedRefine, setQueuedRefine] = useState(false);
  const [committing, setCommitting] = useState<CommitIntent | null>(null);
  const [committingPlanIndex, setCommittingPlanIndex] = useState<number | null>(
    null,
  );
  const abortRef = useRef<AbortController | null>(null);
  const acceptTrackedRef = useRef(false);
  const queuedRefineRef = useRef(false);

  const pathReady = isPathReady(project);
  const pathError = project.path_error ?? null;
  const questions = project.questions ?? [];
  const questionRoundKey = questions.map((q) => q.id).join('|');

  useEffect(() => {
    // Avoid feed churn while restore→commit is in flight.
    if (committing != null) return;
    syncFromProject(project);
  }, [project, syncFromProject, committing]);

  useEffect(() => {
    queuedRefineRef.current = queuedRefine;
  }, [queuedRefine]);

  useEffect(() => {
    if (queuedRefineRef.current) return;
    setAnswers({});
    setComment('');
  }, [questionRoundKey]);

  useEffect(() => {
    if (!pathReady || acceptTrackedRef.current) return;
    acceptTrackedRef.current = true;
    trackAcceptViewed(projectId);
  }, [pathReady, projectId]);

  // Poll while #2 Path is generating.
  useEffect(() => {
    if (pathReady || pathError || busy || committing != null) return;
    const timer = setInterval(() => {
      void (async () => {
        try {
          const detail = await getProject(projectId);
          setProject(detail);
        } catch {
          // Soft-start; next tick retries.
        }
      })();
    }, PATH_POLL_MS);
    return () => clearInterval(timer);
  }, [pathReady, pathError, busy, committing, projectId, setProject]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const hasAnyAnswer = questions.some((q) => Boolean(answers[q.id]?.trim()));
  const hasComment = Boolean(comment.trim());
  // Chips are optional — free-form alone (or any subset of answers) is enough.
  const canRefine =
    !pathError && !busy && committing == null && (hasAnyAnswer || hasComment);

  const waitForPathReady = async (
    signal: AbortSignal,
  ): Promise<ProjectDetail | null> => {
    for (;;) {
      if (signal.aborted) return null;
      const detail = await getProject(projectId, signal);
      if (signal.aborted) return null;
      setProject(detail);
      if (detail.path_error) {
        setError(t('draft.pathError'));
        return null;
      }
      if (isPathReady(detail)) return detail;
      try {
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(resolve, PATH_POLL_MS);
          const onAbort = () => {
            clearTimeout(timer);
            reject(abortError());
          };
          if (signal.aborted) {
            onAbort();
            return;
          }
          signal.addEventListener('abort', onAbort, { once: true });
        });
      } catch (e) {
        if (signal.aborted || isAbortError(e)) return null;
        throw e;
      }
    }
  };

  const formatAnswersTurn = (
    qs: typeof questions,
    ans: Record<string, string>,
    extraComment: string,
  ): string => {
    const lines = qs
      .map((q) => {
        const value = ans[q.id]?.trim();
        return value ? `${q.prompt} → ${value}` : null;
      })
      .filter((line): line is string => Boolean(line));
    if (extraComment.trim()) lines.push(extraComment.trim());
    return lines.join('\n');
  };

  const runRefine = async () => {
    if (busy || pathError || committing != null) return;
    if (!hasAnyAnswer && !hasComment) return;

    // Only send filled answers — unanswered chips are skipped on purpose.
    const answersPayload = questions
      .map((q) => {
        const value = answers[q.id]?.trim();
        return value ? { question_id: q.id, value } : null;
      })
      .filter((row): row is { question_id: string; value: string } =>
        Boolean(row),
      );
    const commentPayload = comment.trim() || null;
    const userText = formatAnswersTurn(questions, answers, commentPayload ?? '');

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const waitingForPath = !pathReady;
    setBusy(true);
    setQueuedRefine(waitingForPath);
    setError(null);

    try {
      if (waitingForPath) {
        const ready = await waitForPathReady(controller.signal);
        if (controller.signal.aborted) return;
        if (!ready) return;
      }
      setQueuedRefine(false);

      const detail = await refineProject(
        projectId,
        { answers: answersPayload, comment: commentPayload },
        controller.signal,
      );
      if (userText) appendUserTurn(userText);
      setProject(detail);
      setAnswers({});
      setComment('');
    } catch (e) {
      if (controller.signal.aborted || isAbortError(e)) return;
      setError(e instanceof ApiError ? e.message : t('draft.error'));
    } finally {
      if (!controller.signal.aborted) {
        setBusy(false);
        setQueuedRefine(false);
      }
    }
  };

  const onCommitFromCard = async (
    snapshot: PlanSnapshot,
    planIndex: number,
    intent: CommitIntent,
  ) => {
    if (committing != null || !snapshot.pathReady || snapshot.pathError) return;
    setCommitting(intent);
    setCommittingPlanIndex(planIndex);
    setError(null);
    try {
      const currentVersion = project.current_version ?? null;
      if (
        snapshot.stateVersion != null &&
        currentVersion != null &&
        snapshot.stateVersion !== currentVersion
      ) {
        // Restore that card's snapshot before commit; do not setProject here
        // (would reshuffle the feed mid-CTA). Reload only if commit fails.
        await restoreState(projectId, snapshot.stateVersion);
      }
      const detail = await commitProject(projectId, 'today');
      clearPlanFeed(projectId);
      setLastProjectId(detail.id);
      if (intent === 'start') {
        navigation.reset({
          index: 1,
          routes: [
            { name: 'Continue' },
            { name: 'Session', params: { projectId: detail.id } },
          ],
        });
        return;
      }
      navigation.reset({
        index: 0,
        routes: [{ name: 'Continue' }],
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('draft.startError'));
      setCommitting(null);
      setCommittingPlanIndex(null);
      try {
        const detail = await getProject(projectId);
        setProject(detail);
      } catch {
        // Keep prior project in memory; user can retry.
      }
    }
  };

  const selectAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  return (
    <SafeScreen scroll>
      <Text style={[styles.feedTitle, { color: colors.textMuted }]}>
        {t('planFeed.title')}
      </Text>

      <View style={styles.feed}>
        {items.map((item) => {
          switch (item.kind) {
            case 'user_turn':
              return (
                <View
                  key={item.id}
                  style={[
                    styles.userBubble,
                    {
                      backgroundColor: colors.surface,
                      borderColor: colors.border,
                    },
                  ]}
                >
                  <Text style={[styles.userText, { color: colors.text }]}>
                    {item.text}
                  </Text>
                </View>
              );
            case 'sense':
              return (
                <View key={item.id} style={styles.senseBlock}>
                  <Text style={[styles.senseLabel, { color: colors.textMuted }]}>
                    {t('planFeed.senseLabel')}
                  </Text>
                  <Text style={[styles.senseText, { color: colors.text }]}>
                    {item.text}
                  </Text>
                </View>
              );
            case 'plan_card':
              return (
                <PlanFeedPlanCard
                  key={item.id}
                  planIndex={item.planIndex}
                  snapshot={item.snapshot}
                  committing={
                    committing != null && committingPlanIndex === item.planIndex
                  }
                  disabled={busy || committing != null}
                  onStart={() =>
                    void onCommitFromCard(item.snapshot, item.planIndex, 'start')
                  }
                  onSaveWithoutStarting={() =>
                    void onCommitFromCard(item.snapshot, item.planIndex, 'save')
                  }
                />
              );
            case 'questions':
              return (
                <PlanFeedQuestions
                  key={item.id}
                  questions={item.questions}
                  answers={answers}
                  comment={comment}
                  disabled={busy || committing != null}
                  canSubmit={canRefine}
                  pathWaiting={!pathReady && !pathError}
                  onSelectAnswer={selectAnswer}
                  onChangeComment={setComment}
                  onSubmit={() => void runRefine()}
                />
              );
            case 'system_note':
              return (
                <Text
                  key={item.id}
                  style={[styles.systemNote, { color: colors.textSecondary }]}
                >
                  {item.text}
                </Text>
              );
            default: {
              const _exhaustive: never = item;
              return _exhaustive;
            }
          }
        })}
      </View>

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}

      {busy ? (
        <View style={styles.busyRow}>
          <ActivityIndicator color={colors.primary} />
          <Text
            style={[styles.muted, { color: colors.textSecondary, flex: 1 }]}
          >
            {queuedRefine ? t('draft.refineQueued') : t('draft.working')}
          </Text>
          <Pressable
            onPress={() => {
              abortRef.current?.abort();
              setBusy(false);
              setQueuedRefine(false);
            }}
            hitSlop={8}
          >
            <Text style={{ color: colors.primary }}>{t('common.cancel')}</Text>
          </Pressable>
        </View>
      ) : null}
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  feedTitle: {
    ...typography.label,
    marginBottom: spacing.md,
  },
  feed: {
    gap: spacing.md,
    paddingBottom: spacing.md,
  },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '92%',
    borderWidth: StyleSheet.hairlineWidth,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  userText: {
    ...typography.body,
  },
  senseBlock: {
    gap: spacing.xs,
    paddingVertical: spacing.xs,
  },
  senseLabel: {
    ...typography.label,
  },
  senseText: {
    ...typography.body,
  },
  systemNote: {
    ...typography.caption,
  },
  muted: {
    ...typography.caption,
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
});
