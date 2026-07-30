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
  getProject,
  listStateVersions,
  refineProject,
  restoreState,
} from '@/api/projects';
import { findBackTarget } from '@/features/draft/backTarget';
import type { RootScreenProps } from '@/navigation/types';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PathList } from '@/shared/ui/PathList';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

export function DraftStudioScreen({
  navigation,
  route,
}: RootScreenProps<'DraftStudio'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId, seed } = route.params;
  const [project, setProject] = useState<ProjectDetail | null>(
    () => seed ?? null,
  );
  const [loading, setLoading] = useState(!seed);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState('');
  const [canGoBack, setCanGoBack] = useState(false);
  const undoStackRef = useRef<number[]>([]);
  const abortRef = useRef<AbortController | null>(null);

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
  const canRefine =
    !busy &&
    (allAnswered || (questions.length === 0 && Boolean(comment.trim())));

  const runRefine = async () => {
    if (!project || busy) return;
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
    if (busy || !project) return;

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

      <PathList
        groups={project.groups}
        actions={project.actions}
        days={project.days}
        cycle={project.cycle}
      />

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
                disabled={busy}
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
            editable={!busy}
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
        </View>
      ) : (
        <Text style={[styles.ready, { color: colors.textSecondary }]}>
          {t('draft.readyHint')}
        </Text>
      )}

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
          disabled={!canGoBack || busy}
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
        label={t('draft.toAccept')}
        disabled={busy}
        onPress={() => navigation.navigate('Accept', { projectId })}
        style={styles.toAccept}
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
  toAccept: {
    marginTop: spacing.md,
  },
});
