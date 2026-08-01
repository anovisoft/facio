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
  TextInput,
  View,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { ApiError } from '@/api/types';
import type { ProjectDetail } from '@/api/types';
import {
  commitProject,
  getProject,
  listStateVersions,
  refineProject,
  restoreState,
} from '@/api/projects';
import { findBackTarget } from '@/features/draft/backTarget';
import type { RootScreenProps } from '@/navigation/types';
import { trackAcceptViewed } from '@/services/beacons';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PathList } from '@/shared/ui/PathList';
import { PlanOutline } from '@/shared/ui/PlanOutline';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const PATH_POLL_MS = 1500;

type CommitIntent = 'start' | 'save';

export function DraftStudioScreen({
  navigation,
  route,
}: RootScreenProps<'DraftStudio'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const { projectId, seed } = route.params;
  const [project, setProject] = useState<ProjectDetail | null>(
    () => seed ?? null,
  );
  const [loading, setLoading] = useState(!seed);
  const [busy, setBusy] = useState(false);
  const [committing, setCommitting] = useState<CommitIntent | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState('');
  const [canGoBack, setCanGoBack] = useState(false);
  const [planExpanded, setPlanExpanded] = useState(false);
  // True while a refine tap is queued behind the path #2 background load —
  // CTA is pressable early; under the hood we wait, then refine.
  const [queuedRefine, setQueuedRefine] = useState(false);
  const undoStackRef = useRef<number[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const acceptTrackedRef = useRef(false);
  const queuedRefineRef = useRef(false);

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('draft.title') });
  }, [navigation, t]);

  const refreshBackAvailability = useCallback(
    async (detail: ProjectDetail, signal?: AbortSignal) => {
      if (undoStackRef.current.length > 0) {
        setCanGoBack(true);
        return;
      }
      try {
        const versions = await listStateVersions(projectId, signal);
        setCanGoBack(
          findBackTarget(versions, detail.current_version) != null,
        );
      } catch {
        setCanGoBack(false);
      }
    },
    [projectId],
  );

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    if (!seed) setLoading(true);
    setError(null);
    try {
      const detail = await getProject(projectId, controller.signal);
      setProject(detail);
      await refreshBackAvailability(detail, controller.signal);
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof ApiError ? e.message : t('draft.error'));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [projectId, refreshBackAvailability, seed, t]);

  useFocusEffect(
    useCallback(() => {
      if (seed) {
        void refreshBackAvailability(seed);
      }
      void load();
      return () => abortRef.current?.abort();
    }, [load, refreshBackAvailability, seed]),
  );

  const pathError = project?.path_error ?? null;
  const pathReady =
    !pathError &&
    project?.path_ready !== false &&
    (project?.actions.length ?? 0) > 0;

  // Poll while full Path is still generating in the background.
  useEffect(() => {
    if (!project || pathReady || pathError || busy || committing != null) return;
    const timer = setInterval(() => {
      void (async () => {
        try {
          const detail = await getProject(projectId);
          setProject(detail);
        } catch {
          // Keep showing start surface; next tick retries.
        }
      })();
    }, PATH_POLL_MS);
    return () => clearInterval(timer);
  }, [project, pathReady, pathError, busy, committing, projectId]);

  useEffect(() => {
    if (!pathReady || acceptTrackedRef.current) return;
    acceptTrackedRef.current = true;
    trackAcceptViewed(projectId);
  }, [pathReady, projectId]);

  useEffect(() => {
    queuedRefineRef.current = queuedRefine;
  }, [queuedRefine]);

  // Only reset when the question *set* changes — not when path #2 bumps version
  // (that was wiping answers the user already picked while the plan loaded).
  const questionRoundKey = project?.questions.map((q) => q.id).join('|') ?? '';

  useEffect(() => {
    // A queued refine is holding the user's answers while it waits for
    // path #2 — don't let a question-set bump underneath it wipe them.
    if (queuedRefineRef.current) return;
    setAnswers({});
    setComment('');
  }, [questionRoundKey]);

  const selectAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const questions = project?.questions ?? [];
  const allAnswered =
    questions.length > 0 &&
    questions.every((q) => Boolean(answers[q.id]?.trim()));
  // Choice: user can pick answers (and press refine) while path #2 still
  // loads in the background — we queue the refine and wait, rather than
  // blocking the CTA on pathReady.
  const canRefine =
    !pathError &&
    !busy &&
    committing == null &&
    (allAnswered || (questions.length === 0 && Boolean(comment.trim())));

  // Poll until path #2 lands (or errors / is aborted). Resolves with the
  // ready project, or null when the wait ended without one (error already
  // surfaced via setError; aborted callers check controller.signal).
  const waitForPathReady = useCallback(
    async (signal: AbortSignal): Promise<ProjectDetail | null> => {
      for (;;) {
        if (signal.aborted) return null;
        const detail = await getProject(projectId, signal);
        if (signal.aborted) return null;
        setProject(detail);
        if (detail.path_error) {
          setError(t('draft.pathError'));
          return null;
        }
        const ready =
          detail.path_ready !== false && (detail.actions?.length ?? 0) > 0;
        if (ready) return detail;
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(resolve, PATH_POLL_MS);
          const onAbort = () => {
            clearTimeout(timer);
            reject(new DOMException('Aborted', 'AbortError'));
          };
          if (signal.aborted) {
            onAbort();
            return;
          }
          signal.addEventListener('abort', onAbort, { once: true });
        });
      }
    },
    [projectId, t],
  );

  const runRefine = async () => {
    if (!project || busy || pathError) return;
    if (questions.length > 0 && !allAnswered) return;
    if (questions.length === 0 && !comment.trim()) return;

    // Freeze the answers/comment the user already entered — the wait below
    // may bump project.questions (path #2 landing); the refine call must
    // still go out with what the user actually picked, not a wiped state.
    const answersPayload = questions.map((q) => ({
      question_id: q.id,
      value: answers[q.id].trim(),
    }));
    const commentPayload = comment.trim() || null;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const waitingForPath = !pathReady;
    setBusy(true);
    setQueuedRefine(waitingForPath);
    setError(null);

    let pushedVersion = false;
    try {
      let target = project;
      if (waitingForPath) {
        const ready = await waitForPathReady(controller.signal);
        if (controller.signal.aborted) return;
        if (!ready) return;
        target = ready;
      }
      setQueuedRefine(false);

      if (target.current_version != null) {
        undoStackRef.current.push(target.current_version);
        pushedVersion = true;
      }

      const detail = await refineProject(
        projectId,
        { answers: answersPayload, comment: commentPayload },
        controller.signal,
      );
      setProject(detail);
      setAnswers({});
      setComment('');
      await refreshBackAvailability(detail, controller.signal);
    } catch (e) {
      if (controller.signal.aborted) return;
      if (pushedVersion) undoStackRef.current.pop();
      setError(e instanceof ApiError ? e.message : t('draft.error'));
    } finally {
      if (!controller.signal.aborted) {
        setBusy(false);
        setQueuedRefine(false);
      }
    }
  };

  const goBackVersion = async () => {
    if (busy || committing != null || !project) return;

    let target: number | null = null;
    if (undoStackRef.current.length > 0) {
      target = undoStackRef.current.pop() ?? null;
    } else {
      try {
        const versions = await listStateVersions(projectId);
        target = findBackTarget(versions, project.current_version);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : t('draft.error'));
        return;
      }
    }
    if (target == null) {
      setCanGoBack(false);
      return;
    }

    setBusy(true);
    setError(null);
    try {
      const detail = await restoreState(projectId, target);
      setProject(detail);
      await refreshBackAvailability(detail);
    } catch (e) {
      undoStackRef.current.push(target);
      setError(e instanceof ApiError ? e.message : t('draft.error'));
    } finally {
      setBusy(false);
    }
  };

  const onCommit = async (intent: CommitIntent) => {
    if (committing != null || !pathReady) return;
    setCommitting(intent);
    setError(null);
    try {
      const detail = await commitProject(projectId, 'today');
      setLastProjectId(detail.id);
      if (intent === 'start') {
        navigation.reset({
          index: 1,
          routes: [
            { name: 'Projects' },
            { name: 'ProjectHome', params: { projectId: detail.id } },
          ],
        });
        return;
      }
      navigation.reset({
        index: 0,
        routes: [{ name: 'Projects' }],
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('draft.startError'));
      setCommitting(null);
    }
  };

  if (loading && !project) {
    return (
      <SafeScreen>
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.muted, { color: colors.textSecondary }]}>
            {t('draft.loading')}
          </Text>
        </View>
      </SafeScreen>
    );
  }

  if (!project) {
    return (
      <SafeScreen>
        <View style={styles.center}>
          <Text style={[styles.error, { color: colors.error }]}>
            {error ?? t('draft.error')}
          </Text>
          <PrimaryButton label={t('projects.retry')} onPress={() => void load()} />
        </View>
      </SafeScreen>
    );
  }

  const paraphrase =
    project.paraphrase || project.outcome || project.raw_intent;
  const planTitle = project.title || project.outcome;
  const planSummary = project.summary;
  const showFullPlan = pathReady && planExpanded;

  return (
    <SafeScreen
      scroll
      footer={
        <>
          <View style={styles.actions}>
            <PrimaryButton
              variant="secondary"
              label={t('draft.back')}
              disabled={!canGoBack || busy || committing != null}
              onPress={() => void goBackVersion()}
              style={styles.actionBtn}
            />
            <PrimaryButton
              variant="secondary"
              label={t('draft.refine')}
              disabled={!canRefine}
              onPress={() => void runRefine()}
              style={styles.actionBtn}
            />
          </View>
          <PrimaryButton
            label={t('draft.saveAndStart')}
            disabled={!pathReady || busy || committing != null}
            loading={committing === 'start'}
            onPress={() => void onCommit('start')}
          />
          <PrimaryButton
            variant="secondary"
            label={t('draft.saveOnly')}
            disabled={!pathReady || busy || committing != null}
            loading={committing === 'save'}
            onPress={() => void onCommit('save')}
          />
        </>
      }
    >
      <Text style={[styles.softStart, { color: colors.text }]}>
        {t('draft.softStart', { paraphrase })}
      </Text>

      {planTitle ? (
        <Text style={[styles.planTitle, { color: colors.text }]}>
          {planTitle}
        </Text>
      ) : null}
      {planSummary ? (
        <Text style={[styles.planSummary, { color: colors.textSecondary }]}>
          {planSummary}
        </Text>
      ) : null}

      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('draft.outlineLabel')}
      </Text>
      <PlanOutline days={project.days} />
      {!pathReady ? (
        <View style={styles.pathLoading}>
          {pathError ? (
            <Text style={[styles.error, { color: colors.error, flex: 1 }]}>
              {t('draft.pathError')}
            </Text>
          ) : (
            <>
              <ActivityIndicator color={colors.primary} />
              <Text
                style={[styles.muted, { color: colors.textSecondary, flex: 1 }]}
              >
                {t('draft.pathLoading')}
              </Text>
            </>
          )}
        </View>
      ) : (
        <Pressable onPress={() => setPlanExpanded((v) => !v)} hitSlop={8}>
          <Text style={[styles.toggle, { color: colors.primary }]}>
            {showFullPlan ? t('draft.hideFullPlan') : t('draft.viewFullPlan')}
          </Text>
        </Pressable>
      )}

      {showFullPlan ? (
        <View style={styles.fullPlan}>
          <PathList
            groups={project.groups}
            actions={project.actions}
            days={project.days}
            cycle={project.cycle}
          />
          {project.success_criteria || project.horizon ? (
            <View style={styles.contract}>
              {project.success_criteria ? (
                <>
                  <Text
                    style={[styles.metaLabel, { color: colors.textMuted }]}
                  >
                    {t('draft.success')}
                  </Text>
                  <Text style={[styles.meta, { color: colors.text }]}>
                    {project.success_criteria}
                  </Text>
                </>
              ) : null}
              {project.horizon ? (
                <>
                  <Text
                    style={[styles.metaLabel, { color: colors.textMuted }]}
                  >
                    {t('draft.horizon')}
                  </Text>
                  <Text style={[styles.meta, { color: colors.text }]}>
                    {project.horizon}
                  </Text>
                </>
              ) : null}
            </View>
          ) : null}
        </View>
      ) : null}

      {questions.length > 0 ? (
        <View style={styles.clarify}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
            {t('draft.clarifyLabel')}
          </Text>
          {questions.map((question, index) => (
            <View key={question.id} style={styles.questionBlock}>
              <Text style={[styles.question, { color: colors.text }]}>
                {index + 1}. {question.prompt}
              </Text>
              <ClarifyChips
                options={question.options}
                selected={answers[question.id] ?? null}
                disabled={busy || committing != null}
                allowCustom
                customPlaceholder={t('draft.freeTextPlaceholder')}
                onSelect={(option) => selectAnswer(question.id, option)}
              />
            </View>
          ))}
        </View>
      ) : pathReady ? (
        <Text style={[styles.ready, { color: colors.textSecondary }]}>
          {t('draft.readyHint')}
        </Text>
      ) : null}

      <View style={styles.commentSection}>
        <Text style={[styles.commentLabel, { color: colors.textMuted }]}>
          {t('draft.commentLabel')}
        </Text>
        <TextInput
          value={comment}
          onChangeText={setComment}
          editable={!busy && committing == null}
          multiline
          placeholder={t('draft.commentPlaceholder')}
          placeholderTextColor={colors.textMuted}
          style={[
            styles.input,
            {
              color: colors.text,
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
        />
        {!pathReady ? (
          <Text style={[styles.muted, { color: colors.textSecondary }]}>
            {t('draft.refineWaitPath')}
          </Text>
        ) : null}
      </View>

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}

      {busy ? (
        <View style={styles.busyRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.muted, { color: colors.textSecondary, flex: 1 }]}>
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
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  softStart: {
    ...typography.title,
    marginBottom: spacing.lg,
  },
  planTitle: {
    ...typography.subtitle,
    marginBottom: spacing.sm,
  },
  planSummary: {
    ...typography.body,
    marginBottom: spacing.md,
  },
  pathLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
    paddingVertical: spacing.sm,
  },
  sectionLabel: {
    ...typography.label,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  toggle: {
    ...typography.caption,
    marginTop: spacing.sm,
    fontWeight: '600',
  },
  fullPlan: {
    marginTop: spacing.md,
  },
  clarify: {
    marginTop: spacing.lg,
    gap: spacing.md,
  },
  questionBlock: {
    gap: spacing.sm,
  },
  question: {
    ...typography.subtitle,
  },
  commentSection: {
    marginTop: spacing.lg,
    gap: spacing.sm,
  },
  commentLabel: {
    ...typography.label,
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    minHeight: 72,
    textAlignVertical: 'top',
  },
  ready: {
    ...typography.body,
    marginTop: spacing.lg,
  },
  contract: {
    marginTop: spacing.lg,
  },
  metaLabel: {
    ...typography.label,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  meta: {
    ...typography.body,
  },
  error: {
    ...typography.caption,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  muted: {
    ...typography.caption,
  },
  busyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  actionBtn: {
    flex: 1,
  },
});
