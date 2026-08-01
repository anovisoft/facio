import React, { useState } from 'react';
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
} from 'react-native';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  visible: boolean;
  busy?: boolean;
  onConfirm: (partialNotes: string) => void;
  onClose: () => void;
};

/** Explicit «Завершить цикл» with optional partial notes. */
export function FinishCycleSheet({
  visible,
  busy,
  onConfirm,
  onClose,
}: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const [notes, setNotes] = useState('');

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
            {t('home.finishCycle')}
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            {t('home.finishCycleSubtitle')}
          </Text>
          <Text style={[styles.commentLabel, { color: colors.textMuted }]}>
            {t('home.finishCycleNotesLabel')}
          </Text>
          <TextInput
            value={notes}
            onChangeText={setNotes}
            editable={!busy}
            multiline
            placeholder={t('home.finishCycleNotesPlaceholder')}
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
            label={t('home.finishCycleConfirm')}
            loading={busy}
            disabled={busy}
            onPress={() => onConfirm(notes.trim())}
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
