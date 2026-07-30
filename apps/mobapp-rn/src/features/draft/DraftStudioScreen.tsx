import React, {
  useCallback,
  useLayoutEffect,
  useRef,
  useState,
} from 'react';
import {
  ActivityIndicator,
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
  const [freeText, setFreeText] = useState('');
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

  const runRefine = async (answer: string, questionId?: string | null) => {
    const trimmed = answer.trim();
    if (!trimmed || busy || !project) return;

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
        trimmed,
        questionId,
        controller.signal,
      );
      setProject(detail);
      setFreeText('');
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

  const question = project.questions[0] ?? null;
  const paraphrase =
    project.paraphrase || project.outcome || project.raw_intent;

  return (
    <SafeScreen scroll>
      <Text style={[styles.softStart, { color: colors.text }]}>
        {t('draft.softStart', { paraphrase })}
      </Text>

      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
        {t('draft.pathLabel')}
      </Text>
      <PathList
        groups={project.groups}
        actions={project.actions}
        compact
      />

      {question ? (
        <View style={styles.clarify}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
            {t('draft.clarifyLabel')}
          </Text>
          <Text style={[styles.question, { color: colors.text }]}>
            {question.prompt}
          </Text>
          <ClarifyChips
            options={question.options}
            disabled={busy}
            onSelect={(option) => void runRefine(option, question.id)}
          />
          <TextInput
            value={freeText}
            onChangeText={setFreeText}
            editable={!busy}
            placeholder={t('draft.freeTextPlaceholder')}
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
          <Text style={[styles.muted, { color: colors.textSecondary }]}>
            {t('draft.working')}
          </Text>
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
          disabled={busy || !freeText.trim()}
          onPress={() =>
            void runRefine(freeText, question?.id ?? null)
          }
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
  sectionLabel: {
    ...typography.label,
    marginTop: spacing.lg,
    marginBottom: spacing.sm,
  },
  clarify: {
    marginTop: spacing.sm,
    gap: spacing.sm,
  },
  question: {
    ...typography.subtitle,
    marginBottom: spacing.xs,
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    marginTop: spacing.sm,
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
