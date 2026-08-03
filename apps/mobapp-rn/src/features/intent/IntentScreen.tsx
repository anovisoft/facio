import React, { useLayoutEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useTranslation } from 'react-i18next';

import { ApiError } from '@/api/types';
import { createProject } from '@/api/projects';
import type { RootScreenProps } from '@/navigation/types';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import { useSessionStore } from '@/store';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const EXAMPLE_INTENTS = [
  'Приготовить карбонару',
  'Навести порядок в квартире',
  'Подготовиться к собеседованию',
] as const;

/** Create screen (Facio 0.1) — IntentScreen alias. Instant Answer off happy path (D5). */
export function IntentScreen({ navigation }: RootScreenProps<'Create'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setLastProjectId = useSessionStore((s) => s.setLastProjectId);
  const [intent, setIntent] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('intent.title') });
  }, [navigation, t]);

  const submit = async (raw: string) => {
    const trimmed = raw.trim();
    if (!trimmed || loading) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    try {
      const result = await createProject(trimmed, controller.signal);
      // D5: Instant Answer removed from Create happy path — ask for a goal.
      if (result.kind === 'instant_answer') {
        setError(t('intent.instantAnswerRedirect'));
        return;
      }
      setLastProjectId(result.project.id);
      navigation.replace('GuideExplore', {
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
      <Text style={[styles.prompt, { color: colors.text }]}>
        {t('intent.title')}
      </Text>

      <TextInput
        value={intent}
        onChangeText={setIntent}
        placeholder={t('intent.placeholder')}
        placeholderTextColor={colors.textMuted}
        editable={!loading}
        multiline
        style={[
          styles.input,
          {
            color: colors.text,
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}
      />

      <Text style={[styles.examplesLabel, { color: colors.textMuted }]}>
        {t('intent.examplesLabel')}
      </Text>
      <ClarifyChips
        options={[...EXAMPLE_INTENTS]}
        disabled={loading}
        onSelect={(option) => {
          setIntent(option);
          void submit(option);
        }}
      />

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
      ) : (
        <PrimaryButton
          label={t('intent.submit')}
          onPress={() => void submit(intent)}
          disabled={!intent.trim()}
          style={styles.submit}
        />
      )}
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  prompt: {
    ...typography.title,
    marginBottom: spacing.md,
  },
  input: {
    ...typography.body,
    minHeight: 96,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    textAlignVertical: 'top',
    marginBottom: spacing.lg,
  },
  examplesLabel: {
    ...typography.caption,
    marginBottom: spacing.sm,
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
  submit: {
    marginTop: spacing.xl,
  },
});
