import React, { useCallback, useLayoutEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { ApiError } from '@/api/types';
import type { FirstStepWhen, ProjectDetail } from '@/api/types';
import { commitProject, getProject } from '@/api/projects';
import type { RootScreenProps } from '@/navigation/types';
import { trackAcceptViewed } from '@/services/beacons';
import { PathList } from '@/shared/ui/PathList';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

export function AcceptScreen({
  navigation,
  route,
}: RootScreenProps<'Accept'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const { projectId } = route.params;
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [when, setWhen] = useState<FirstStepWhen>('today');

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('accept.title') });
  }, [navigation, t]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const detail = await getProject(projectId);
      setProject(detail);
      trackAcceptViewed(projectId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : t('accept.error'));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const onCommit = async () => {
    if (committing) return;
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
      setError(e instanceof ApiError ? e.message : t('accept.error'));
      setCommitting(false);
    }
  };

  if (loading && !project) {
    return (
      <SafeScreen>
        <View style={styles.center}>
          <ActivityIndicator color={colors.primary} />
        </View>
      </SafeScreen>
    );
  }

  if (!project) {
    return (
      <SafeScreen>
        <View style={styles.center}>
          <Text style={[styles.error, { color: colors.error }]}>
            {error ?? t('accept.error')}
          </Text>
          <PrimaryButton label={t('projects.retry')} onPress={() => void load()} />
        </View>
      </SafeScreen>
    );
  }

  const planTitle =
    project.title || project.outcome || project.paraphrase || project.raw_intent;

  return (
    <SafeScreen scroll>
      <Text style={[styles.outcomeLabel, { color: colors.textMuted }]}>
        {t('accept.goal')}
      </Text>
      <Text style={[styles.outcome, { color: colors.text }]}>{planTitle}</Text>

      {project.summary ? (
        <Text style={[styles.summary, { color: colors.textSecondary }]}>
          {project.summary}
        </Text>
      ) : null}

      {project.success_criteria ? (
        <>
          <Text style={[styles.metaLabel, { color: colors.textMuted }]}>
            {t('accept.success')}
          </Text>
          <Text style={[styles.meta, { color: colors.text }]}>
            {project.success_criteria}
          </Text>
        </>
      ) : null}

      {project.horizon ? (
        <>
          <Text style={[styles.metaLabel, { color: colors.textMuted }]}>
            {t('accept.horizon')}
          </Text>
          <Text style={[styles.meta, { color: colors.text }]}>
            {project.horizon}
          </Text>
        </>
      ) : null}

      <Text style={[styles.pathLabel, { color: colors.textMuted }]}>
        {t('path.title')}
      </Text>
      <PathList groups={project.groups} actions={project.actions} />

      <Text style={[styles.whenLabel, { color: colors.text }]}>
        {t('accept.firstStepWhen')}
      </Text>
      <View style={styles.whenRow}>
        {(['today', 'tomorrow'] as const).map((option) => {
          const selected = when === option;
          return (
            <Pressable
              key={option}
              onPress={() => setWhen(option)}
              disabled={committing}
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
                  ? t('accept.today')
                  : t('accept.tomorrow')}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}

      <PrimaryButton
        label={t('accept.commit')}
        loading={committing}
        onPress={() => void onCommit()}
        style={styles.commit}
      />
      <PrimaryButton
        variant="ghost"
        label={t('accept.moreClarify')}
        disabled={committing}
        onPress={() => {
          if (navigation.canGoBack()) {
            navigation.goBack();
            return;
          }
          navigation.navigate('DraftStudio', { projectId });
        }}
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
  outcomeLabel: {
    ...typography.label,
    marginBottom: spacing.xs,
  },
  outcome: {
    ...typography.title,
    marginBottom: spacing.sm,
  },
  summary: {
    ...typography.body,
    marginBottom: spacing.lg,
  },
  metaLabel: {
    ...typography.label,
    marginTop: spacing.sm,
    marginBottom: spacing.xs,
  },
  meta: {
    ...typography.body,
  },
  pathLabel: {
    ...typography.label,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
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
  commit: {
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
  },
});
