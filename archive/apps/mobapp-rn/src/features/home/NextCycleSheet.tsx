import React, { useState } from 'react';
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
} from 'react-native';
import { useTranslation } from '../../../node_modules/react-i18next';

import type { ContinueKind } from '@/api/types';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  visible: boolean;
  busy?: boolean;
  continueKind: ContinueKind;
  continueLabel?: string | null;
  onConfirm: (comment: string) => void;
  onClose: () => void;
};

/** Clarify-before-N+1 sheet: comment + CTA (docs/next/05 next cycle). */
export function NextCycleSheet({
  visible,
  busy,
  continueKind,
  continueLabel,
  onConfirm,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [comment, setComment] = useState('');

  const ctaLabel =
    continueKind === 'repeat'
      ? t('home.repeatCycle')
      : t('home.nextCycle');

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={busy ? undefined : onClose}
    >
      <Pressable
        style={[styles.backdrop, { backgroundColor: colors.overlay }]}
        onPress={busy ? undefined : onClose}
      >
        <Pressable
          style={[
            styles.card,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
          onPress={(e) => e.stopPropagation()}
        >
          <Text style={[styles.title, { color: colors.text }]}>
            {ctaLabel}
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            {continueLabel || t('home.nextCycleSubtitle')}
          </Text>
          <Text style={[styles.commentLabel, { color: colors.textMuted }]}>
            {t('home.nextCycleCommentLabel')}
          </Text>
          <TextInput
            value={comment}
            onChangeText={setComment}
            editable={!busy}
            multiline
            placeholder={t('home.nextCycleCommentPlaceholder')}
            placeholderTextColor={colors.textMuted}
            style={[
              styles.input,
              {
                color: colors.text,
                borderColor: colors.border,
                backgroundColor: colors.surfaceMuted,
              },
            ]}
          />
          <PrimaryButton
            label={ctaLabel}
            loading={busy}
            disabled={busy}
            onPress={() => onConfirm(comment.trim())}
          />
          <Pressable onPress={onClose} disabled={busy} hitSlop={8}>
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
  commentLabel: {
    ...typography.caption,
    marginBottom: spacing.xs,
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: radii.md,
    padding: spacing.md,
    minHeight: 72,
    textAlignVertical: 'top',
    marginBottom: spacing.lg,
  },
  cancel: {
    ...typography.body,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
