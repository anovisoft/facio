import React, { useEffect, useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radii, spacing, typography } from '@/theme';

type WhenModalProps = {
  visible: boolean;
  initialHours: number;
  initialMinutes: number;
  onSave: (hours: number, minutes: number) => void;
  onClose: () => void;
};

function wrap(value: number, max: number): number {
  return (value + max) % max;
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

export function WhenModal({
  visible,
  initialHours,
  initialMinutes,
  onSave,
  onClose,
}: WhenModalProps) {
  const [hours, setHours] = useState(initialHours);
  const [minutes, setMinutes] = useState(initialMinutes);

  useEffect(() => {
    if (visible) {
      setHours(initialHours);
      setMinutes(initialMinutes);
    }
  }, [visible, initialHours, initialMinutes]);

  return (
    <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View style={styles.sheet}>
          <Text style={styles.title}>когда напомнить</Text>

          <View style={styles.clock}>
            <Stepper
              value={hours}
              label="часы"
              onStep={(delta) => setHours((current) => wrap(current + delta, 24))}
            />
            <Text style={styles.colon}>:</Text>
            <Stepper
              value={minutes}
              label="минуты"
              onStep={(delta) => setMinutes((current) => wrap(current + delta, 60))}
            />
          </View>

          <Pressable
            onPress={() => onSave(hours, minutes)}
            style={({ pressed }) => [styles.save, pressed && styles.pressed]}
          >
            <Text style={styles.saveText}>Сохранить</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

function Stepper({
  value,
  label,
  onStep,
}: {
  value: number;
  label: string;
  onStep: (delta: number) => void;
}) {
  return (
    <View style={styles.stepper}>
      <Pressable
        onPress={() => onStep(1)}
        style={({ pressed }) => [styles.nudge, pressed && styles.pressed]}
        accessibilityLabel={`${label} плюс`}
      >
        <Text style={styles.nudgeText}>+</Text>
      </Pressable>
      <Text style={styles.digits} accessibilityLabel={label}>
        {pad(value)}
      </Text>
      <Pressable
        onPress={() => onStep(-1)}
        style={({ pressed }) => [styles.nudge, pressed && styles.pressed]}
        accessibilityLabel={`${label} минус`}
      >
        <Text style={styles.nudgeText}>−</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(26, 26, 24, 0.28)',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  sheet: {
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
  },
  title: {
    ...typography.subtitle,
    color: colors.text,
    textAlign: 'center',
  },
  clock: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.md,
    gap: spacing.sm,
  },
  colon: {
    ...typography.hero,
    color: colors.textMuted,
    marginTop: -8,
  },
  stepper: {
    alignItems: 'center',
    gap: spacing.xs,
  },
  nudge: {
    width: 48,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  nudgeText: {
    fontSize: 22,
    fontWeight: '600',
    color: colors.primary,
  },
  digits: {
    ...typography.hero,
    color: colors.text,
    minWidth: 88,
    textAlign: 'center',
  },
  save: {
    marginTop: spacing.lg,
    backgroundColor: colors.primary,
    borderRadius: radii.lg,
    paddingVertical: spacing.md,
    alignItems: 'center',
  },
  saveText: {
    ...typography.subtitle,
    color: colors.white,
  },
  pressed: {
    opacity: 0.7,
  },
});
