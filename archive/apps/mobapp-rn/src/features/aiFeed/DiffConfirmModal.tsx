import React from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type { RepairDiffLine } from '@/api/types';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  visible: boolean;
  busy?: boolean;
  diff: RepairDiffLine[];
  summary?: string | null;
  onConfirm: () => void;
  onClose: () => void;
};

/**
 * Human-readable Diff confirm step before applying an Active AI proposal.
 * Extracted from RepairSheet (Slice E) — reused by Active AI Feed (E2c).
 */
export function DiffConfirmModal({
  visible,
  busy,
  diff,
  summary,
  onConfirm,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  const handleClose = () => {
    if (busy) return;
    onClose();
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
          <Text style={[styles.title, { color: colors.text }]}>
            {t('aiFeed.diffTitle')}
          </Text>
          {summary ? (
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              {summary}
            </Text>
          ) : (
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              {t('aiFeed.diffSubtitle')}
            </Text>
          )}
          <ScrollView
            style={styles.diffScroll}
            contentContainerStyle={styles.diffList}
          >
            {diff.map((line, index) => (
              <View
                key={`${line.before}-${line.after}-${index}`}
                style={[styles.diffRow, { borderBottomColor: colors.border }]}
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
          {busy ? (
            <View style={styles.previewing}>
              <ActivityIndicator color={colors.primary} />
              <Text style={[styles.previewingText, { color: colors.textMuted }]}>
                {t('aiFeed.applying')}
              </Text>
            </View>
          ) : null}
          <PrimaryButton
            label={t('aiFeed.confirm')}
            disabled={busy || diff.length === 0}
            loading={busy}
            onPress={onConfirm}
          />
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
  previewing: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.md,
  },
  previewingText: {
    ...typography.caption,
  },
  cancel: {
    ...typography.body,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
