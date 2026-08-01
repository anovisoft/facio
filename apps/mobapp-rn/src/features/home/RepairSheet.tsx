import React from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { RepairIntent } from '@/api/types';
import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  visible: boolean;
  busy?: boolean;
  onPick: (intent: RepairIntent) => void;
  onClose: () => void;
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

/** Structured «Не могу» gesture (docs/next/05 Repair UX): pick an intent. */
export function RepairSheet({ visible, busy, onPick, onClose }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
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
                loading={busy}
                onPress={() => onPick(intent)}
              />
            ))}
          </View>
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
  options: {
    gap: spacing.sm,
  },
  cancel: {
    ...typography.body,
    textAlign: 'center',
    marginTop: spacing.lg,
  },
});
