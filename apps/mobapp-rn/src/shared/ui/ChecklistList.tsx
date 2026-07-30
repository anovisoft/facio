import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { ChecklistItemResponse } from '@/api/types';
import { useTheme } from '@/theme/ThemeContext';
import { radii, spacing, typography } from '@/theme';

type Props = {
  items: ChecklistItemResponse[];
  disabled?: boolean;
  onToggle?: (item: ChecklistItemResponse, nextDone: boolean) => void;
};

export function ChecklistList({ items, disabled, onToggle }: Props) {
  const { colors } = useTheme();
  if (items.length === 0) return null;

  const sorted = [...items].sort((a, b) => a.sort - b.sort);

  return (
    <View style={styles.root}>
      {sorted.map((item) => {
        const interactive = Boolean(onToggle) && !disabled;
        return (
          <Pressable
            key={item.id}
            disabled={!interactive}
            onPress={() => onToggle?.(item, !item.done)}
            style={styles.row}
            hitSlop={4}
          >
            <View
              style={[
                styles.box,
                {
                  borderColor: item.done ? colors.primary : colors.border,
                  backgroundColor: item.done
                    ? colors.primary
                    : colors.surface,
                },
              ]}
            >
              {item.done ? (
                <Text style={[styles.check, { color: colors.white }]}>✓</Text>
              ) : null}
            </View>
            <Text
              style={[
                styles.title,
                {
                  color: item.done ? colors.textSecondary : colors.text,
                  textDecorationLine: item.done ? 'line-through' : 'none',
                },
              ]}
            >
              {item.title}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    gap: spacing.sm,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: spacing.sm,
  },
  box: {
    width: 22,
    height: 22,
    borderRadius: radii.sm,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 1,
  },
  check: {
    fontSize: 13,
    fontWeight: '700',
    lineHeight: 16,
  },
  title: {
    ...typography.body,
    flex: 1,
  },
});
