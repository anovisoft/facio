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

import { ApiError, type ProjectDetail } from '@/api/types';
import { getProject } from '@/api/projects';
import { CompactRoadmap } from '@/features/guide/CompactRoadmap';
import { GuideContractGlance } from '@/features/guide/GuideContractGlance';
import { GuideCoverHeader } from '@/features/guide/GuideCoverHeader';
import { PlanFeedExplore } from '@/features/guide/planFeed/PlanFeedExplore';
import type { RootScreenProps } from '@/navigation/types';
import { trackPathOpened } from '@/services/beacons';
import { PathList } from '@/shared/ui/PathList';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

type Props = RootScreenProps<'Guide'> | RootScreenProps<'GuideExplore'>;

/**
 * Guide trust surface (Facio 0.1):
 * - Draft / Explore → Plan Feed (Slice E2a)
 * - Active → Cover + Compact roadmap + Start Session
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
  const [error, setError] = useState<string | null>(null);
  const [detailExpanded, setDetailExpanded] = useState(fromSession);
  const abortRef = useRef<AbortController | null>(null);
  const pathTrackedRef = useRef(false);

  const isDraft = project?.status === 'draft';

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('guide.title') });
  }, [navigation, t]);

  const load = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    if (!seed) setLoading(true);
    setError(null);
    try {
      const detail = await getProject(projectId, controller.signal);
      setProject(detail);
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
  }, [projectId, seed, t]);

  useFocusEffect(
    useCallback(() => {
      void load();
      return () => abortRef.current?.abort();
    }, [load]),
  );

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

  if (isDraft) {
    return (
      <PlanFeedExplore
        navigation={navigation}
        projectId={projectId}
        project={project}
        setProject={setProject}
        error={error}
        setError={setError}
      />
    );
  }

  const pathReady =
    !project.path_error &&
    project.path_ready !== false &&
    (project.actions.length ?? 0) > 0;
  const showDetail = pathReady && detailExpanded;

  const stickyFooter = fromSession ? (
    <View style={styles.footerCol}>
      <PrimaryButton
        variant="secondary"
        label={t('guide.editPlan')}
        onPress={() =>
          navigation.navigate('ActiveAiFeed', { projectId: project.id })
        }
      />
      <PrimaryButton
        variant="ghost"
        label={t('guide.backToSession')}
        onPress={() => navigation.goBack()}
      />
    </View>
  ) : (
    <View style={styles.footerCol}>
      <PrimaryButton
        variant="secondary"
        label={t('guide.editPlan')}
        onPress={() =>
          navigation.navigate('ActiveAiFeed', { projectId: project.id })
        }
      />
      {project.next_action ? (
        <PrimaryButton
          label={t('guide.startSession')}
          onPress={onStartSession}
        />
      ) : null}
    </View>
  );

  return (
    <SafeScreen scroll footer={stickyFooter}>
      <GuideCoverHeader guide={project} />
      <GuideContractGlance guide={project} />

      {pathReady ? (
        <View style={styles.roadmapBlock}>
          <CompactRoadmap actions={project.actions} days={project.days} />
          <Pressable
            onPress={() => setDetailExpanded((v) => !v)}
            hitSlop={8}
          >
            <Text style={[styles.toggle, { color: colors.primary }]}>
              {showDetail ? t('guide.hideDetail') : t('guide.viewDetail')}
            </Text>
          </Pressable>
        </View>
      ) : null}

      {showDetail ? (
        <View style={styles.fullPlan}>
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

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
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
  roadmapBlock: {
    marginBottom: spacing.md,
  },
  toggle: {
    ...typography.caption,
    marginTop: spacing.sm,
    fontWeight: '600',
  },
  fullPlan: {
    marginTop: spacing.md,
  },
  error: {
    ...typography.caption,
    marginTop: spacing.md,
    textAlign: 'center',
  },
  muted: {
    ...typography.caption,
  },
  footerCol: {
    gap: spacing.sm,
  },
});
