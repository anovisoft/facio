import React, { useEffect, useLayoutEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type { RepairIntent } from '@/api/types';
import { DiffConfirmModal } from '@/features/aiFeed/DiffConfirmModal';
import { ProposalCard } from '@/features/aiFeed/ProposalCard';
import type { AiFeedProposal } from '@/features/aiFeed/types';
import { useActiveAiFeed } from '@/features/aiFeed/useActiveAiFeed';
import { ClarifyChips } from '@/shared/ui/ClarifyChips';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { SafeScreen } from '@/shared/ui/SafeScreen';
import type { RootScreenProps } from '@/navigation/types';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

const INTENTS: RepairIntent[] = ['shift', 'lighten', 'rest'];

function intentLabelKey(intent: RepairIntent): string {
  switch (intent) {
    case 'shift':
      return 'home.repairShift';
    case 'lighten':
      return 'home.repairLighten';
    case 'rest':
      return 'home.repairRest';
    default: {
      const _exhaustive: never = intent;
      return _exhaustive;
    }
  }
}

type PendingApply = {
  itemId: string;
  proposal: AiFeedProposal;
};

/**
 * Active AI Feed — repair lenta for living Guides (Slice E2c).
 * Intents + freeform → proposal cards → Diff → confirm → Undo on Session.
 */
export function ActiveAiFeedScreen({
  navigation,
  route,
}: RootScreenProps<'ActiveAiFeed'>) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const { projectId, seedReason, initialIntent, openManual } = route.params;

  const {
    items,
    busy,
    error,
    setError,
    runPreview,
    applyProposal,
    markSeeded,
    wasSeeded,
  } = useActiveAiFeed(projectId);

  const [composer, setComposer] = useState('');
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [pendingApply, setPendingApply] = useState<PendingApply | null>(null);

  useLayoutEffect(() => {
    navigation.setOptions({ title: t('aiFeed.title') });
  }, [navigation, t]);

  // Seed once: Manual → Rebuild with AI, or intent chip from ManualEdit.
  useEffect(() => {
    if (wasSeeded()) return;
    if (!seedReason && !initialIntent) return;
    markSeeded();
    const reason =
      seedReason?.trim() ||
      (initialIntent === 'lighten'
        ? t('aiFeed.seedLighten')
        : initialIntent === 'shift'
          ? t('aiFeed.seedShift')
          : initialIntent === 'rest'
            ? t('aiFeed.seedRest')
            : '');
    const userText =
      seedReason?.trim() ||
      (initialIntent ? t(intentLabelKey(initialIntent)) : reason);
    void runPreview({
      reason,
      intent: initialIntent ?? null,
      userText,
    });
  }, [
    initialIntent,
    markSeeded,
    runPreview,
    seedReason,
    t,
    wasSeeded,
  ]);

  const latestQuestions = useMemo(() => {
    for (let i = items.length - 1; i >= 0; i -= 1) {
      const item = items[i];
      if (item?.kind === 'questions') return item;
    }
    return null;
  }, [items]);

  const onIntent = (intent: RepairIntent) => {
    if (busy) return;
    void runPreview({
      reason: t(
        intent === 'lighten'
          ? 'aiFeed.seedLighten'
          : intent === 'shift'
            ? 'aiFeed.seedShift'
            : 'aiFeed.seedRest',
      ),
      intent,
      userText: t(intentLabelKey(intent)),
    });
  };

  const onSubmitComposer = () => {
    if (busy) return;
    const note = composer.trim();
    const answerParts = Object.entries(answers)
      .filter(([, v]) => v.trim())
      .map(([id, v]) => `${id}: ${v.trim()}`);
    const reasonParts = [...answerParts];
    if (note) reasonParts.push(note);
    if (reasonParts.length === 0) return;
    const reason = reasonParts.join('\n');
    setComposer('');
    setAnswers({});
    void runPreview({
      reason,
      userText: note || reason,
    });
  };

  const onConfirmApply = async () => {
    if (!pendingApply || busy) return;
    const result = await applyProposal(
      pendingApply.proposal,
      pendingApply.itemId,
    );
    if (!result) return;
    setPendingApply(null);
    navigation.navigate({
      name: 'Session',
      params: {
        projectId,
        undoVersion: result.undoVersion,
        undoMessage: t('aiFeed.applied'),
      },
      merge: true,
    });
  };

  const canSubmit =
    composer.trim().length > 0 ||
    Object.values(answers).some((v) => v.trim().length > 0);

  return (
    <SafeScreen
      scroll
      footer={
        <View style={styles.footer}>
          {openManual !== false ? (
            <PrimaryButton
              variant="ghost"
              label={t('aiFeed.editTools')}
              disabled={busy}
              onPress={() =>
                navigation.navigate('ManualEdit', {
                  projectId,
                  mode: 'active',
                })
              }
            />
          ) : null}
          <Text style={[styles.composerLabel, { color: colors.textSecondary }]}>
            {t('aiFeed.composerLabel')}
          </Text>
          <TextInput
            value={composer}
            onChangeText={setComposer}
            editable={!busy}
            placeholder={t('aiFeed.composerPlaceholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.composer,
              {
                color: colors.text,
                borderColor: colors.border,
                backgroundColor: colors.surface,
              },
            ]}
            multiline
            textAlignVertical="top"
          />
          <PrimaryButton
            label={t('aiFeed.send')}
            disabled={busy || !canSubmit}
            loading={busy && canSubmit}
            onPress={onSubmitComposer}
          />
        </View>
      }
    >
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
        {t('aiFeed.subtitle')}
      </Text>

      <View style={styles.chips}>
        {INTENTS.map((intent) => (
          <Pressable
            key={intent}
            disabled={busy}
            onPress={() => onIntent(intent)}
            style={[
              styles.chip,
              {
                borderColor: colors.border,
                backgroundColor: colors.surface,
                opacity: busy ? 0.5 : 1,
              },
            ]}
          >
            <Text style={[styles.chipText, { color: colors.text }]}>
              {t(intentLabelKey(intent))}
            </Text>
          </Pressable>
        ))}
      </View>

      {busy && items.length === 0 ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.muted, { color: colors.textMuted }]}>
            {t('aiFeed.previewing')}
          </Text>
        </View>
      ) : null}

      <View style={styles.feed}>
        {items.map((item) => {
          switch (item.kind) {
            case 'user_turn':
              return (
                <View
                  key={item.id}
                  style={[
                    styles.bubble,
                    styles.userBubble,
                    { backgroundColor: colors.surfaceMuted },
                  ]}
                >
                  <Text style={{ color: colors.text }}>{item.text}</Text>
                </View>
              );
            case 'sense':
              return (
                <Text
                  key={item.id}
                  style={[styles.sense, { color: colors.textSecondary }]}
                >
                  {item.text}
                </Text>
              );
            case 'proposal_card':
              return (
                <ProposalCard
                  key={item.id}
                  proposalIndex={item.proposalIndex}
                  proposal={item.proposal}
                  applied={item.applied}
                  disabled={busy}
                  onReview={() =>
                    setPendingApply({
                      itemId: item.id,
                      proposal: item.proposal,
                    })
                  }
                />
              );
            case 'questions':
              return (
                <View
                  key={item.id}
                  style={[
                    styles.questions,
                    {
                      borderColor: colors.border,
                      backgroundColor: colors.surface,
                    },
                  ]}
                >
                  <Text
                    style={[styles.questionsTitle, { color: colors.text }]}
                  >
                    {t('aiFeed.questionsTitle')}
                  </Text>
                  {item.questions.map((q) => (
                    <View key={q.id} style={styles.questionBlock}>
                      <Text
                        style={[
                          styles.questionPrompt,
                          { color: colors.textSecondary },
                        ]}
                      >
                        {q.prompt}
                      </Text>
                      <ClarifyChips
                        options={q.options}
                        selected={answers[q.id]}
                        selection={q.selection === 'multi' ? 'single' : q.selection}
                        disabled={busy || latestQuestions?.id !== item.id}
                        onSelect={(value) =>
                          setAnswers((prev) => ({ ...prev, [q.id]: value }))
                        }
                      />
                    </View>
                  ))}
                </View>
              );
            case 'system_note': {
              const text =
                item.text === 'no_changes'
                  ? t('aiFeed.noChanges')
                  : item.text === 'preview_failed'
                    ? t('aiFeed.previewError')
                    : item.text === 'apply_failed'
                      ? t('aiFeed.applyError')
                      : item.text;
              return (
                <Text
                  key={item.id}
                  style={[styles.note, { color: colors.textMuted }]}
                >
                  {text}
                </Text>
              );
            }
            default: {
              const _exhaustive: never = item;
              return _exhaustive;
            }
          }
        })}
      </View>

      {busy && items.length > 0 ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator color={colors.primary} />
          <Text style={[styles.muted, { color: colors.textMuted }]}>
            {t('aiFeed.previewing')}
          </Text>
        </View>
      ) : null}

      {error ? (
        <Text style={[styles.error, { color: colors.error }]}>
          {error === 'preview_failed'
            ? t('aiFeed.previewError')
            : error === 'apply_failed'
              ? t('aiFeed.applyError')
              : error}
        </Text>
      ) : null}

      <DiffConfirmModal
        visible={pendingApply != null}
        busy={busy}
        diff={pendingApply?.proposal.diff ?? []}
        summary={pendingApply?.proposal.summary}
        onConfirm={() => void onConfirmApply()}
        onClose={() => {
          if (!busy) {
            setPendingApply(null);
            setError(null);
          }
        }}
      />
    </SafeScreen>
  );
}

const styles = StyleSheet.create({
  subtitle: {
    ...typography.body,
    marginBottom: spacing.md,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  chip: {
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipText: {
    ...typography.caption,
    fontWeight: '600',
  },
  feed: {
    gap: spacing.md,
  },
  bubble: {
    borderRadius: radii.md,
    padding: spacing.md,
  },
  userBubble: {
    alignSelf: 'flex-end',
    maxWidth: '92%',
  },
  sense: {
    ...typography.body,
  },
  questions: {
    borderWidth: 1,
    borderRadius: radii.lg,
    padding: spacing.md,
    gap: spacing.md,
  },
  questionsTitle: {
    ...typography.body,
    fontWeight: '600',
  },
  questionBlock: {
    gap: spacing.sm,
  },
  questionPrompt: {
    ...typography.caption,
  },
  note: {
    ...typography.caption,
  },
  loadingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  muted: {
    ...typography.caption,
  },
  error: {
    ...typography.caption,
    marginTop: spacing.sm,
  },
  footer: {
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    gap: spacing.sm,
  },
  composerLabel: {
    ...typography.caption,
  },
  composer: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    minHeight: 72,
    lineHeight: 22,
  },
});
