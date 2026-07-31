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
import type { FirstStepWhen, ProjectDetail } from '@/api/types';
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
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const PATH_POLL_MS = 1500;

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
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState('');
  const [canGoBack, setCanGoBack] = useState(false);
  const [when, setWhen] = useState<FirstStepWhen>('today');
  const undoStackRef = useRef<number[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const acceptTrackedRef = useRef(false);

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
    if (!project || pathReady || pathError || busy || committing) return;
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

  const questionRoundKey = project?.questions.map((q) => q.id).join('|') ?? '';

  useEffect(() => {
    setAnswers({});
    setComment('');
  }, [questionRoundKey, project?.current_version]);

  const selectAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const questions = project?.questions ?? [];
  const allAnswered =
    questions.length > 0 &&
    questions.every((q) => Boolean(answers[q.id]?.trim()));
  // Choice: user can pick answers while path loads, but refine waits for path_ready.
  const canRefine =
    pathReady &&
    !busy &&
    !committing &&
    (allAnswered || (questions.length === 0 && Boolean(comment.trim())));

  const runRefine = async () => {
    if (!project || busy || !pathReady) return;
    if (questions.length > 0 && !allAnswered) return;
    if (questions.length === 0 && !comment.trim()) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    if (project.current_version != null) {
      undoStackRef.current.push(project.current_version);
    }

    setBusy(true);
    setError(null);
    try {
      const detail = await refineProject(
        projectId,
        {
          answers: questions.map((q) => ({
            question_id: q.id,
            value: answers[q.id].trim(),
          })),
          comment: comment.trim() || null,
        },
        controller.signal,
      );
      setProject(detail);
      setAnswers({});
      setComment('');
      await refreshBackAvailability(detail, controller.signal);
    } catch (e) {
      if (controller.signal.aborted) return;
      undoStackRef.current.pop();
      setError(e instanceof ApiError ? e.message : t('draft.error'));
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const goBackVersion = async () => {
    if (busy || committing || !project) return;

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

  const onStartToday = async () => {
    if (committing || !pathReady) return;
    setCommitting(true);
    setError(null);
    try {
      const detail = await commitProject(projectId, when);
      setLastProjectId(detail.id);
      navigation.reset({
        index: 1,
        routes: [
          { name: 'Projects' },
          { name: 'ProjectHome', params: { projectId: detail.id } },
        ],
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('draft.startError'));
      setCommitting(false);
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

  return (
    <SafeScreen scroll>
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
        <PathList
          groups={project.groups}
          actions={project.actions}
          days={project.days}
          cycle={project.cycle}
        />
      )}

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
                disabled={busy || committing}
                allowCustom
                customPlaceholder={t('draft.freeTextPlaceholder')}
                onSelect={(option) => selectAnswer(question.id, option)}
              />
            </View>
          ))}
          <Text style={[styles.commentLabel, { color: colors.textMuted }]}>
            {t('draft.commentLabel')}
          </Text>
          <TextInput
            value={comment}
            onChangeText={setComment}
            editable={!busy && !committing}
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
      ) : pathReady ? (
        <Text style={[styles.ready, { color: colors.textSecondary }]}>
          {t('draft.readyHint')}
        </Text>
      ) : null}

      {pathReady ? (
        <>
          {(project.success_criteria || project.horizon) && (
            <View style={styles.contract}>
              {project.success_criteria ? (
                <>
                  <Text style={[styles.metaLabel, { color: colors.textMuted }]}>
                    {t('draft.success')}
                  </Text>
                  <Text style={[styles.meta, { color: colors.text }]}>
                    {project.success_criteria}
                  </Text>
                </>
              ) : null}
              {project.horizon ? (
                <>
                  <Text style={[styles.metaLabel, { color: colors.textMuted }]}>
                    {t('draft.horizon')}
                  </Text>
                  <Text style={[styles.meta, { color: colors.text }]}>
                    {project.horizon}
                  </Text>
                </>
              ) : null}
            </View>
          )}

          <Text style={[styles.whenLabel, { color: colors.text }]}>
            {t('draft.firstStepWhen')}
          </Text>
          <View style={styles.whenRow}>
            {(['today', 'tomorrow'] as const).map((option) => {
              const selected = when === option;
              return (
                <Pressable
                  key={option}
                  onPress={() => setWhen(option)}
                  disabled={committing || busy}
                  style={[
                    styles.whenChip,
                    {
                      backgroundColor: selected
                        ? colors.primary
                        : colors.surface,
                      borderColor: selected ? colors.primary : colors.border,
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.whenText,
                      { color: selected ? colors.white : colors.primary },
                    ]}
                  >
                    {option === 'today'
                      ? t('draft.today')
                      : t('draft.tomorrow')}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </>
      ) : null}

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}

      {busy ? (
        <View style={styles.busyRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.muted, { color: colors.textSecondary, flex: 1 }]}>
            {t('draft.working')}
          </Text>
          <Pressable
            onPress={() => {
              abortRef.current?.abort();
              setBusy(false);
            }}
            hitSlop={8}
          >
            <Text style={{ color: colors.primary }}>{t('common.cancel')}</Text>
          </Pressable>
        </View>
      ) : null}

      <View style={styles.actions}>
        <PrimaryButton
          variant="secondary"
          label={t('draft.back')}
          disabled={!canGoBack || busy || committing}
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
        label={t('draft.startToday')}
        disabled={!pathReady || busy}
        loading={committing}
        onPress={() => void onStartToday()}
        style={styles.startToday}
      />
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
  clarify: {
    marginTop: spacing.sm,
    gap: spacing.md,
  },
  questionBlock: {
    gap: spacing.sm,
  },
  question: {
    ...typography.subtitle,
  },
  commentLabel: {
    ...typography.label,
    marginTop: spacing.xs,
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
  whenLabel: {
    ...typography.subtitle,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
  whenRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  whenChip: {
    flex: 1,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  whenText: {
    ...typography.subtitle,
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
    marginTop: spacing.lg,
  },
  actionBtn: {
    flex: 1,
  },
  startToday: {
    marginTop: spacing.md,
  },
});
