import React, { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTranslation } from 'react-i18next';

import type { RepairDiffLine, RepairIntent } from '@/api/types';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Phase = 'pick' | 'diff';

type Props = {
  visible: boolean;
  busy?: boolean;
  /** After intent pick — parent runs preview; call `showDiff` or stay on pick with error. */
  onPick: (intent: RepairIntent) => void;
  /** Confirm apply of the previewed Diff. */
  onConfirm: () => void;
  onClose: () => void;
  /** Controlled Diff payload from parent preview. */
  diff: RepairDiffLine[] | null;
  summary?: string | null;
  /** Reset Diff when sheet closes / parent clears. */
  onClearDiff?: () => void;
};

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

/**
 * Repair sheet: pick intent → show before→after Diff → Confirm / Cancel.
 * Facio 0.1 §11.5 / screens §8 — never silent apply.
 */
export function RepairSheet({
  visible,
  busy,
  onPick,
  onConfirm,
  onClose,
  diff,
  summary,
  onClearDiff,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [phase, setPhase] = useState<Phase>('pick');

  useEffect(() => {
    if (!visible) {
      setPhase('pick');
      return;
    }
    if (diff && diff.length > 0) {
      setPhase('diff');
    }
  }, [visible, diff]);

  const handleClose = () => {
    if (busy) return;
    setPhase('pick');
    onClearDiff?.();
    onClose();
  };

  const handleBackToPick = () => {
    if (busy) return;
    setPhase('pick');
    onClearDiff?.();
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={handleClose}
    >
      <Pressable
        style={[styles.backdrop, { backgroundColor: colors.overlay }]}
        onPress={busy ? undefined : handleClose}
      >
        <Pressable
          style={[
            styles.card,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
          onPress={(e) => e.stopPropagation()}
        >
          {phase === 'pick' ? (
            <>
              <Text style={[styles.title, { color: colors.text }]}>
                {t('home.repairTitle')}
              </Text>
              <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
                {t('home.repairSubtitle')}
              </Text>
              <View style={styles.options}>
                {INTENTS.map((intent) => (
                  <PrimaryButton
                    key={intent}
                    variant="secondary"
                    label={t(intentLabelKey(intent))}
                    disabled={busy}
                    onPress={() => onPick(intent)}
                  />
                ))}
              </View>
              {busy ? (
                <View style={styles.previewing}>
                  <ActivityIndicator color={colors.primary} />
                  <Text
                    style={[styles.previewingText, { color: colors.textMuted }]}
                  >
                    {t('home.repairPreviewing')}
                  </Text>
                </View>
              ) : null}
              <Pressable onPress={handleClose} disabled={busy} hitSlop={8}>
                <Text
                  style={[
                    styles.cancel,
                    { color: busy ? colors.textMuted : colors.primary },
                  ]}
                >
                  {t('common.cancel')}
                </Text>
              </Pressable>
            </>
          ) : (
            <>
              <Text style={[styles.title, { color: colors.text }]}>
                {t('home.repairDiffTitle')}
              </Text>
              {summary ? (
                <Text
                  style={[styles.subtitle, { color: colors.textSecondary }]}
                >
                  {summary}
                </Text>
              ) : (
                <Text
                  style={[styles.subtitle, { color: colors.textSecondary }]}
                >
                  {t('home.repairDiffSubtitle')}
                </Text>
              )}
              <ScrollView
                style={styles.diffScroll}
                contentContainerStyle={styles.diffList}
              >
                {(diff ?? []).map((line, index) => (
                  <View
                    key={`${line.before}-${line.after}-${index}`}
                    style={[
                      styles.diffRow,
                      { borderBottomColor: colors.border },
                    ]}
                  >
                    <Text
                      style={[styles.diffBefore, { color: colors.textMuted }]}
                      numberOfLines={2}
                    >
                      {line.before}
                    </Text>
                    <Text
                      style={[styles.diffArrow, { color: colors.textSecondary }]}
                    >
                      →
                    </Text>
                    <Text
                      style={[styles.diffAfter, { color: colors.text }]}
                      numberOfLines={2}
                    >
                      {line.after}
                    </Text>
                  </View>
                ))}
              </ScrollView>
              <PrimaryButton
                label={t('home.repairConfirm')}
                disabled={busy}
                loading={busy}
                onPress={onConfirm}
              />
              <Pressable onPress={handleBackToPick} disabled={busy} hitSlop={8}>
                <Text
                  style={[
                    styles.cancel,
                    { color: busy ? colors.textMuted : colors.primary },
                  ]}
                >
                  {t('common.cancel')}
                </Text>
              </Pressable>
            </>
          )}
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  card: {
    width: '100%',
    maxWidth: 360,
    maxHeight: '80%',
    borderRadius: radii.lg,
    borderWidth: 1,
    padding: spacing.lg,
  },
  title: {
    ...typography.title,
    marginBottom: spacing.xs,
  },
  subtitle: {
    ...typography.body,
    marginBottom: spacing.lg,
  },
  options: {
    gap: spacing.sm,
  },
  previewing: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginTop: spacing.md,
  },
  previewingText: {
    ...typography.caption,
  },
  diffScroll: {
    maxHeight: 220,
    marginBottom: spacing.lg,
  },
  diffList: {
    gap: 0,
  },
  diffRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
  },
  diffBefore: {
    ...typography.body,
    flex: 1,
  },
  diffArrow: {
    ...typography.body,
  },
  diffAfter: {
    ...typography.body,
    flex: 1,
    fontWeight: '600',
  },
  cancel: {
    ...typography.body,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
