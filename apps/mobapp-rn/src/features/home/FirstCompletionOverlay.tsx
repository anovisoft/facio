import React from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { PrimaryButton } from '@/shared/ui/PrimaryButton';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  visible: boolean;
  onContinue: () => void;
};

/** One-shot beat after the first «Сделано» on a project. */
export function FirstCompletionOverlay({ visible, onContinue }: Props) {
  const { t } = useTranslation();
  const { colors } = useTheme();

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onContinue}
    >
      <Pressable
        style={[styles.backdrop, { backgroundColor: colors.overlay }]}
        onPress={onContinue}
      >
        <Pressable
          style={[
            styles.card,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
          onPress={(e) => e.stopPropagation()}
        >
          <Text style={[styles.title, { color: colors.text }]}>
            {t('home.firstCompletionTitle')}
          </Text>
          <Text style={[styles.body, { color: colors.textSecondary }]}>
            {t('home.firstCompletionBody')}
          </Text>
          <PrimaryButton
            label={t('home.firstCompletionCta')}
            onPress={onContinue}
            style={styles.cta}
          />
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
    marginBottom: spacing.sm,
  },
  body: {
    ...typography.body,
  },
  cta: {
    marginTop: spacing.lg,
  },
});
