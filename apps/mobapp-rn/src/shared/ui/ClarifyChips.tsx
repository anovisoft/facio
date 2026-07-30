import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  options: string[];
  onSelect: (option: string) => void;
  disabled?: boolean;
};

export function ClarifyChips({ options, onSelect, disabled }: Props) {
  const { colors } = useTheme();

  return (
    <View style={styles.row}>
      {options.map((option) => (
        <Pressable
          key={option}
          disabled={disabled}
          onPress={() => onSelect(option)}
          style={({ pressed }) => [
            styles.chip,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: disabled ? 0.5 : pressed ? 0.85 : 1,
            },
          ]}
        >
          <Text style={[styles.label, { color: colors.primary }]}>
            {option}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  chip: {
    borderWidth: 1,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  label: {
    ...typography.caption,
  },
});
