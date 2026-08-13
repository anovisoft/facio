import React, { useCallback, useState } from 'react';
import {
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from '../../../node_modules/react-i18next';

import { ApiError, type ProjectStatus, type ProjectSummary } from '@/api/types';
import { listProjects } from '@/api/projects';
import type { RootScreenProps } from '@/navigation/types';
import { AsyncState } from '@/shared/ui/AsyncState';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

function statusLabel(
  status: ProjectStatus,
  t: (key: string) => string,
): string {
  switch (status) {
    case 'abandoned':
      return t('history.abandoned');
    case 'completed':
      return t('history.completed');
    case 'draft':
      return t('projects.draft');
    case 'active':
      return t('home.today');
    default: {
      const _exhaustive: never = status;
      return _exhaustive;
    }
  }
}

/** Archive screen (Facio 0.1) — HistoryScreen alias. */
export function HistoryScreen(_props: RootScreenProps<'Archive'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [items, setItems] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      try {
        const rows = await listProjects('abandoned');
        setItems(rows);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : t('history.error'));
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

  return (
    <SafeScreen>
      <Text style={[styles.title, { color: colors.text }]}>
        {t('history.title')}
      </Text>
      <AsyncState
        loading={loading && !refreshing}
        error={error}
        empty={!loading && !error && items.length === 0}
        emptyMessage={t('history.empty')}
        loadingMessage={t('history.loading')}
        retryLabel={t('history.retry')}
        onRetry={() => void load()}
      >
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void load(true)}
              tintColor={colors.primary}
            />
          }
          renderItem={({ item }) => (
            <View style={[styles.row, { borderBottomColor: colors.border }]}>
              <Text
                style={[styles.rowTitle, { color: colors.text }]}
                numberOfLines={2}
              >
                {item.title || item.outcome || item.raw_intent}
              </Text>
              <Text style={[styles.muted, { color: colors.textSecondary }]}>
                {statusLabel(item.status, t)}
              </Text>
            </View>
          )}
        />
      </AsyncState>
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  title: {
    ...typography.title,
    marginBottom: spacing.md,
  },
  muted: {
    ...typography.caption,
  },
  row: {
    paddingVertical: spacing.md,
    borderBottomWidth: 1,
  },
  rowTitle: {
    ...typography.subtitle,
    marginBottom: spacing.xs,
  },
});
