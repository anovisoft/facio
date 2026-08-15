import React from 'react';
import { Pressable, StyleSheet, Text } from 'react-native';

import { colors } from '@/theme';

/** Visible kebab. Inspect / carousel / chat are later steps — this opens nothing. */
export function KebabStub() {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel="меню"
      hitSlop={8}
      onPress={() => undefined}
      style={styles.hit}
    >
      <Text style={styles.dots}>···</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  hit: {
    minWidth: 28,
    minHeight: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dots: {
    color: colors.textMuted,
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 1,
  },
});
