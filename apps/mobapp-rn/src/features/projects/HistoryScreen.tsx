import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useTranslation } from 'react-i18next';

import { ApiError, type ProjectSummary } from '@/api/types';
import { listProjects } from '@/api/projects';
import type { RootScreenProps } from '@/navigation/types';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

export function HistoryScreen(_props: RootScreenProps<'History'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [items, setItems] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useFocusEffect(
    useCallback(() => {
      let cancelled = false;
      (async () => {
        setLoading(true);
        setError(null);
        try {
          const rows = await listProjects('abandoned');
          if (!cancelled) setItems(rows);
        } catch (e) {
          if (!cancelled) {
            setError(e instanceof ApiError ? e.message : t('projects.error'));
          }
        } finally {
          if (!cancelled) setLoading(false);
        }
      })();
      return () => {
        cancelled = true;
      };
    }, [t]),
  );

  return (
    <SafeScreen>
      <Text style={[styles.title, { color: colors.text }]}>
        {t('history.title')}
      </Text>
      {loading ? (
        <ActivityIndicator color={colors.primary} style={styles.pad} />
      ) : error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.id}
          ListEmptyComponent={
            <Text style={[styles.muted, { color: colors.textSecondary }]}>
              {t('history.empty')}
            </Text>
          }
          renderItem={({ item }) => (
            <View
              style={[styles.row, { borderBottomColor: colors.border }]}
            >
              <Text
                style={[styles.rowTitle, { color: colors.text }]}
                numberOfLines={2}
              >
                {item.outcome || item.raw_intent}
              </Text>
              <Text style={[styles.muted, { color: colors.textSecondary }]}>
                {item.status}
              </Text>
            </View>
          )}
        />
      )}
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  title: {
    ...typography.title,
    marginBottom: spacing.md,
  },
  pad: { marginTop: spacing.xl },
  muted: {
    ...typography.body,
  },
  error: {
    ...typography.body,
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
