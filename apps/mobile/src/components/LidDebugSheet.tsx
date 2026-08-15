import React from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '@/theme';

type LidDebugSheetProps = {
  visible: boolean;
  onClose: () => void;
  onSilence: (days: 8 | 21) => void;
};

export function LidDebugSheet({ visible, onClose, onSilence }: LidDebugSheetProps) {
  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.sheet}>
          <Text style={styles.hint}>на крышке снова появится карточка срыва</Text>
          <Pressable
            onPress={() => onSilence(8)}
            style={({ pressed }) => [styles.row, pressed && styles.pressed]}
          >
            <Text style={styles.rowText}>велосипед молчал 8 дней</Text>
          </Pressable>
          <Pressable
            onPress={() => onSilence(21)}
            style={({ pressed }) => [styles.row, pressed && styles.pressed]}
          >
            <Text style={styles.rowText}>велосипед молчал 21 день</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(26, 26, 24, 0.18)',
    justifyContent: 'flex-end',
    paddingHorizontal: spacing.md,
    paddingBottom: spacing.xl,
  },
  sheet: {
    backgroundColor: colors.surfaceMuted,
    borderRadius: radii.md,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.sm,
    paddingBottom: spacing.sm,
  },
  hint: {
    ...typography.caption,
    color: colors.textMuted,
    marginBottom: spacing.xs,
  },
  row: {
    paddingVertical: spacing.sm,
  },
  rowText: {
    ...typography.caption,
    color: colors.textSecondary,
  },
  pressed: {
    opacity: 0.6,
  },
});
