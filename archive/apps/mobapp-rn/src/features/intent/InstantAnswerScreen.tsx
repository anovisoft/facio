import React, { useLayoutEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import { ApiError } from '@/api/types';
import { createProject } from '@/api/projects';
import type { RootScreenProps } from '@/navigation/types';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { spacing, typography } from '@/theme';

export function InstantAnswerScreen({
  navigation,
  route,
}: RootScreenProps<'InstantAnswer'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const { payload } = route.params;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('instantAnswer.title') });
  }, [navigation, t]);

  const startGoal = async (goal: string) => {
    if (loading) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await createProject(goal, controller.signal);
      if (result.kind === 'instant_answer') {
        navigation.replace('InstantAnswer', { payload: result });
        return;
      }
      setLastProjectId(result.project.id);
      navigation.replace('Guide', {
        projectId: result.project.id,
        seed: result.project,
      });
    } catch (e) {
      if (controller.signal.aborted) return;
      setError(e instanceof ApiError ? e.message : t('intent.error'));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  return (
    <SafeScreen scroll>
      <Text style={[styles.label, { color: colors.textMuted }]}>
        {payload.label}
      </Text>
      <Text style={[styles.answer, { color: colors.text }]}>
        {payload.answer}
      </Text>
      <Text style={[styles.cta, { color: colors.text }]}>
        {t('instantAnswer.cta')}
      </Text>

      {payload.goal_suggestions.length > 0 ? (
        <ClarifyChips
          options={payload.goal_suggestions}
          disabled={loading}
          onSelect={(goal) => void startGoal(goal)}
        />
      ) : null}

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
      ) : null}

      {loading ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            {t('intent.working')}
          </Text>
          <Pressable
            onPress={() => {
              abortRef.current?.abort();
              setLoading(false);
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
  label: {
    ...typography.caption,
    marginBottom: spacing.sm,
  },
  answer: {
    ...typography.body,
    marginBottom: spacing.lg,
  },
  cta: {
    ...typography.subtitle,
    marginBottom: spacing.md,
  },
  error: {
    ...typography.caption,
    marginTop: spacing.md,
  },
  loadingRow: {
    marginTop: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  loadingText: {
    ...typography.caption,
    flex: 1,
  },
});
