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

import { ApiError, type ProjectDetail } from '@/api/types';
import {
  commitProject,
  getProject,
  listStateVersions,
  refineProject,
  restoreState,
} from '@/api/projects';
import { findBackTarget } from '@/features/draft/backTarget';
import { CompactRoadmap } from '@/features/guide/CompactRoadmap';
import { GuideContractGlance } from '@/features/guide/GuideContractGlance';
import { GuideCoverHeader } from '@/features/guide/GuideCoverHeader';
import { softStartDisplayLine } from '@/features/guide/softStartDisplay';
import type { RootScreenProps } from '@/navigation/types';
import { trackAcceptViewed, trackPathOpened } from '@/services/beacons';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PathList } from '@/shared/ui/PathList';
import { PlanOutline } from '@/shared/ui/PlanOutline';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const PATH_POLL_MS = 1500;
const PATH_READY_FLASH_MS = 2200;

/** RN Hermes has no DOM AbortError type — reject wait polls with a plain Error. */
function abortError(): Error {
  const err = new Error('Aborted');
  err.name = 'AbortError';
  return err;
}

function isAbortError(e: unknown): boolean {
  return e instanceof Error && e.name === 'AbortError';
}

type CommitIntent = 'start' | 'save';

type Props = RootScreenProps<'Guide'> | RootScreenProps<'GuideExplore'>;

/**
 * Guide trust surface (Facio 0.1 Slice C) — draft Explore + active roadmap.
 * Cover + contract + Compact Summaries + sticky Start Guide / Start Session.
 * Commitment is CTA on this screen (D4) — no Accept duplicate map.
 */
export function GuideScreen({ navigation, route }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const { projectId } = route.params;
  const seed = 'seed' in route.params ? route.params.seed : undefined;
  const fromSession = route.params.fromSession === true;

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
  // From Session ≡ → full plan open by default; drawer/Create stay compact-first.
  const [detailExpanded, setDetailExpanded] = useState(fromSession);
  const [queuedRefine, setQueuedRefine] = useState(false);
  const [pathReadyFlash, setPathReadyFlash] = useState(false);
  const undoStackRef = useRef<number[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const acceptTrackedRef = useRef(false);
  const pathTrackedRef = useRef(false);
  const queuedRefineRef = useRef(false);
  const prevPathReadyRef = useRef<boolean | null>(null);
  const flashTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isDraft = project?.status === 'draft';

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('guide.title') });
  }, [navigation, t]);

  const refreshBackAvailability = useCallback(
    async (detail: ProjectDetail, signal?: AbortSignal) => {
      if (detail.status !== 'draft') {
        setCanGoBack(false);
        return;
      }
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
      if (!pathTrackedRef.current && detail.status !== 'draft') {
        pathTrackedRef.current = true;
        trackPathOpened(projectId);
      }
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof ApiError ? e.message : t('guide.error'));
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

  // Poll while full Path (#2) is still generating in the background.
  useEffect(() => {
    if (
      !project ||
      !isDraft ||
      pathReady ||
      pathError ||
      busy ||
      committing != null
    ) {
      return;
    }
    const timer = setInterval(() => {
      void (async () => {
        try {
          const detail = await getProject(projectId);
          setProject(detail);
        } catch {
          // Keep showing soft-start; next tick retries.
        }
      })();
    }, PATH_POLL_MS);
    return () => clearInterval(timer);
  }, [
    project,
    isDraft,
    pathReady,
    pathError,
    busy,
    committing,
    projectId,
  ]);

  useEffect(() => {
    if (!isDraft || !pathReady || acceptTrackedRef.current) return;
    acceptTrackedRef.current = true;
    trackAcceptViewed(projectId);
  }, [isDraft, pathReady, projectId]);

  // Light flash when path_ready flips false → true (don't auto-scroll aggressively).
  useEffect(() => {
    const prev = prevPathReadyRef.current;
    prevPathReadyRef.current = pathReady;
    if (!isDraft || !pathReady || prev !== false) return;
    setPathReadyFlash(true);
    if (flashTimerRef.current) clearTimeout(flashTimerRef.current);
    flashTimerRef.current = setTimeout(() => {
      setPathReadyFlash(false);
      flashTimerRef.current = null;
    }, PATH_READY_FLASH_MS);
    return () => {
      if (flashTimerRef.current) {
        clearTimeout(flashTimerRef.current);
        flashTimerRef.current = null;
      }
    };
  }, [isDraft, pathReady]);

  useEffect(() => {
    queuedRefineRef.current = queuedRefine;
  }, [queuedRefine]);

  const questionRoundKey = project?.questions.map((q) => q.id).join('|') ?? '';

  useEffect(() => {
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
  const canRefine =
    isDraft &&
    !pathError &&
    !busy &&
    committing == null &&
    (allAnswered || (questions.length === 0 && Boolean(comment.trim())));

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
    },
    [projectId, t],
  );

  const runRefine = async () => {
    if (!project || !isDraft || busy || pathError) return;
    if (questions.length > 0 && !allAnswered) return;
    if (questions.length === 0 && !comment.trim()) return;

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
      if (controller.signal.aborted || isAbortError(e)) return;
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
    if (!isDraft || busy || committing != null || !project) return;

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
    if (committing != null || !pathReady || !isDraft) return;
    setCommitting(intent);
    setError(null);
    try {
      const detail = await commitProject(projectId, 'today');
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
    }
  };

  const onStartSession = () => {
    if (!project?.next_action) return;
    setLastProjectId(project.id);
    navigation.navigate('Session', { projectId: project.id });
  };

  if (loading && !project) {
    return (
      <SafeScreen>
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.muted, { color: colors.textSecondary }]}>
            {t('guide.loading')}
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
            {error ?? t('guide.error')}
          </Text>
          <PrimaryButton label={t('projects.retry')} onPress={() => void load()} />
        </View>
      </SafeScreen>
    );
  }

  const paraphrase =
    project.paraphrase || project.outcome || project.raw_intent;
  const hasCoverTitle = Boolean(
    project.title || project.outcome || project.raw_intent,
  );
  /** Soft-start only when Cover has no title yet — never softStart line + Cover twin. */
  const softStartForCover =
    isDraft && !hasCoverTitle && paraphrase
      ? softStartDisplayLine(paraphrase, (bare) =>
          t('draft.softStart', { paraphrase: bare }),
        )
      : null;
  const showDetail = pathReady && detailExpanded;
  /** Soft-start outline while #2 loads (or failed) — before Compact roadmap. */
  const showOutlineWhileLoading = isDraft && !pathReady;

  // Sticky footer: Start Guide only (+ optional tertiary save). No Back/Refine.
  // Active + from Session: Back to Session (Start Session is useless — stack back).
  // Active from drawer/Continue/Create: Start Session when next_action exists.
  const stickyFooter = isDraft ? (
    <>
      <PrimaryButton
        label={t('guide.startGuide')}
        disabled={!pathReady || busy || committing != null}
        loading={committing === 'start'}
        onPress={() => void onCommit('start')}
      />
      <Pressable
        accessibilityRole="button"
        disabled={!pathReady || busy || committing != null}
        onPress={() => void onCommit('save')}
        hitSlop={8}
        style={styles.saveLink}
      >
        <Text
          style={[
            styles.saveLinkText,
            {
              color:
                !pathReady || busy || committing != null
                  ? colors.textMuted
                  : colors.textSecondary,
            },
          ]}
        >
          {committing === 'save'
            ? t('draft.working')
            : t('draft.saveWithoutStarting')}
        </Text>
      </Pressable>
    </>
  ) : fromSession ? (
    <PrimaryButton
      variant="secondary"
      label={t('guide.backToSession')}
      onPress={() => navigation.goBack()}
    />
  ) : project.next_action ? (
    <PrimaryButton
      label={t('guide.startSession')}
      onPress={onStartSession}
    />
  ) : null;

  return (
    <SafeScreen scroll footer={stickyFooter}>
      <GuideCoverHeader guide={project} softStartLine={softStartForCover} />
      <GuideContractGlance guide={project} />

      {isDraft && canGoBack ? (
        <Pressable
          accessibilityRole="button"
          disabled={busy || committing != null}
          onPress={() => void goBackVersion()}
          hitSlop={8}
          style={styles.versionBack}
        >
          <Text
            style={[
              styles.versionBackText,
              {
                color:
                  busy || committing != null
                    ? colors.textMuted
                    : colors.textSecondary,
              },
            ]}
          >
            {t('draft.versionBack')}
          </Text>
        </Pressable>
      ) : null}

      {showOutlineWhileLoading ? (
        <View style={styles.roadmapBlock}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
            {t('draft.outlineLabel')}
          </Text>
          <PlanOutline days={project.days} />
          <View style={styles.pathLoading}>
            {pathError ? (
              <Text style={[styles.error, { color: colors.error, flex: 1 }]}>
                {t('draft.pathError')}
              </Text>
            ) : (
              <>
                <ActivityIndicator color={colors.primary} />
                <Text
                  style={[
                    styles.muted,
                    { color: colors.textSecondary, flex: 1 },
                  ]}
                >
                  {t('draft.pathLoading')}
                </Text>
              </>
            )}
          </View>
        </View>
      ) : null}

      {pathReady ? (
        <View style={styles.roadmapBlock}>
          <View
            style={[
              styles.pathReadyBanner,
              {
                backgroundColor: pathReadyFlash
                  ? colors.surfaceMuted
                  : colors.surface,
                borderColor: pathReadyFlash ? colors.primary : colors.border,
              },
            ]}
          >
            <Text
              style={[
                styles.pathReadyText,
                {
                  color: pathReadyFlash ? colors.primary : colors.textSecondary,
                },
              ]}
            >
              {t('guide.pathReady')}
            </Text>
          </View>
          <CompactRoadmap actions={project.actions} days={project.days} />
          <Pressable
            onPress={() => setDetailExpanded((v) => !v)}
            hitSlop={8}
          >
            <Text style={[styles.toggle, { color: colors.primary }]}>
              {showDetail
                ? t('guide.hideDetail')
                : t('guide.viewDetail')}
            </Text>
          </Pressable>
        </View>
      ) : null}

      {pathError && !showOutlineWhileLoading ? (
        <Text style={[styles.error, { color: colors.error }]}>
          {t('draft.pathError')}
        </Text>
      ) : null}

      {showDetail ? (
        <View style={styles.fullPlan}>
          {/*
            expandable: steps start collapsed — avoids N× Full Block / stepper
            minHeight voids that felt like scroll-into-empty (P1).
            Tap a step to expand detail; plugins stay preview-only.
          */}
          <PathList
            groups={project.groups}
            actions={project.actions}
            days={project.days}
            cycle={project.cycle}
            expandable
            pluginsInteractive={false}
          />
        </View>
      ) : null}

      {isDraft && questions.length > 0 ? (
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
          <PrimaryButton
            variant="secondary"
            label={t('draft.refine')}
            disabled={!canRefine}
            onPress={() => void runRefine()}
          />
        </View>
      ) : isDraft && pathReady ? (
        <Text style={[styles.ready, { color: colors.textSecondary }]}>
          {t('guide.readyHint')}
        </Text>
      ) : null}

      {isDraft ? (
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
          {questions.length === 0 ? (
            <PrimaryButton
              variant="secondary"
              label={t('draft.refine')}
              disabled={!canRefine}
              onPress={() => void runRefine()}
              style={styles.refineAfterComment}
            />
          ) : null}
        </View>
      ) : null}

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
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  versionBack: {
    alignSelf: 'flex-start',
    marginBottom: spacing.md,
  },
  versionBackText: {
    ...typography.caption,
    fontWeight: '600',
  },
  pathReadyBanner: {
    alignSelf: 'flex-start',
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
    borderRadius: radii.sm,
    borderWidth: StyleSheet.hairlineWidth,
    marginBottom: spacing.sm,
  },
  pathReadyText: {
    ...typography.caption,
    fontWeight: '700',
  },
  roadmapBlock: {
    marginBottom: spacing.md,
  },
  pathLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.sm,
    paddingVertical: spacing.sm,
  },
  sectionLabel: {
    ...typography.label,
    marginTop: spacing.sm,
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
  refineAfterComment: {
    marginTop: spacing.sm,
  },
  ready: {
    ...typography.body,
    marginTop: spacing.lg,
  },
  saveLink: {
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  saveLinkText: {
    ...typography.caption,
    fontWeight: '600',
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
});
