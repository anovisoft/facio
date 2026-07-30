import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { ApiError } from '@/api/types';
import type { ProjectSummary } from '@/api/types';
import { listProjects } from '@/api/projects';
import type { RootScreenProps } from '@/navigation/types';
import { trackProjectSwitched } from '@/services/beacons';
import { GlassFab } from '@/shared/ui/GlassFab';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { ThemeModeSwitcher } from '@/shared/ui/ThemeModeSwitcher';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

export function ProjectsScreen({ navigation }: RootScreenProps<'Projects'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const themeMode = useSessionStore((s) => s.themeMode);
  const setThemeMode = useSessionStore((s) => s.setThemeMode);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      try {
        const rows = await listProjects('open');
        setProjects(rows);
      } catch (e) {
        const message =
          e instanceof ApiError ? e.message : t('projects.error');
        setError(message);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [t],
  );

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load]),
  );

  const openProject = (project: ProjectSummary) => {
    setLastProjectId(project.id);
    trackProjectSwitched(project.id);
    if (project.status === 'draft') {
      navigation.navigate('DraftStudio', { projectId: project.id });
      return;
    }
    navigation.navigate('ProjectHome', { projectId: project.id });
  };

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <SafeScreen style={styles.flex}>
        <View style={styles.header}>
          <Text style={[styles.title, { color: colors.text }]}>
            {t('projects.title')}
          </Text>
          <Pressable onPress={() => navigation.navigate('History')} hitSlop={8}>
            <Text style={[styles.link, { color: colors.primary }]}>
              {t('projects.history')}
            </Text>
          </Pressable>
        </View>

        <View style={styles.themeRow}>
          <ThemeModeSwitcher value={themeMode} onChange={setThemeMode} />
        </View>

        {loading && !refreshing ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.primary} />
            <Text style={[styles.muted, { color: colors.textSecondary }]}>
              {t('projects.loading')}
            </Text>
          </View>
        ) : error ? (
          <View style={styles.center}>
            <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
            <PrimaryButton
              label={t('projects.retry')}
              onPress={() => void load()}
            />
          </View>
        ) : (
          <FlatList
            data={projects}
            keyExtractor={(item) => item.id}
            contentContainerStyle={
              projects.length === 0
                ? styles.emptyContainer
                : [styles.list, { paddingBottom: 100 }]
            }
            refreshControl={
              <RefreshControl
                refreshing={refreshing}
                onRefresh={() => void load(true)}
                tintColor={colors.primary}
              />
            }
            ListEmptyComponent={
              <Text style={[styles.muted, { color: colors.textSecondary }]}>
                {t('projects.empty')}
              </Text>
            }
            style={styles.listFlex}
            renderItem={({ item }) => (
              <Pressable
                style={[
                  styles.card,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                  },
                ]}
                onPress={() => openProject(item)}
              >
                <View style={styles.cardTop}>
                  <Text
                    style={[styles.cardTitle, { color: colors.text }]}
                    numberOfLines={2}
                  >
                    {item.title || item.outcome || item.raw_intent}
                  </Text>
                  {item.status === 'draft' ? (
                    <Text
                      style={[
                        styles.badge,
                        {
                          color: colors.primary,
                          backgroundColor: colors.surfaceMuted,
                        },
                      ]}
                    >
                      {t('projects.draft')}
                    </Text>
                  ) : null}
                </View>
                {item.status === 'active' && item.next_action?.title ? (
                  <Text
                    style={[styles.cardSub, { color: colors.textSecondary }]}
                    numberOfLines={2}
                  >
                    {t('projects.nextAction', {
                      title: item.next_action.title,
                    })}
                  </Text>
                ) : null}
              </Pressable>
            )}
          />
        )}
      </SafeScreen>

      <GlassFab onPress={() => navigation.navigate('Intent')} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  flex: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  title: {
    ...typography.hero,
  },
  link: {
    ...typography.caption,
  },
  themeRow: {
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.md,
  },
  muted: {
    ...typography.body,
    textAlign: 'center',
  },
  error: {
    ...typography.body,
    textAlign: 'center',
    marginBottom: spacing.sm,
  },
  listFlex: {
    flex: 1,
  },
  list: {
    gap: spacing.sm,
  },
  emptyContainer: {
    flexGrow: 1,
    justifyContent: 'center',
  },
  card: {
    borderRadius: radii.md,
    borderWidth: 1,
    padding: spacing.md,
    marginBottom: spacing.sm,
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  cardTitle: {
    ...typography.subtitle,
    flex: 1,
  },
  badge: {
    ...typography.label,
    overflow: 'hidden',
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: radii.pill,
  },
  cardSub: {
    ...typography.caption,
    marginTop: spacing.xs,
  },
});
