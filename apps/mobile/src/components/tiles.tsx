import React, { useEffect } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { Cue, Widget } from '@/domain/types';
import { colors, radii, spacing, typography } from '@/theme';
import { KebabStub } from './KebabStub';

type CounterTileProps = {
  widget: Widget;
  cue?: Cue;
  onOpen: () => void;
  onSurfaced: () => void;
};

export function CounterTile({ widget, cue, onOpen, onSurfaced }: CounterTileProps) {
  const count = widget.payload.count ?? 0;
  const target = widget.payload.target ?? 0;

  useEffect(() => {
    if (cue) onSurfaced();
  }, [cue, onSurfaced]);

  return (
    <View style={styles.card}>
      <View style={styles.top}>
        <Pressable onPress={onOpen} style={styles.topHit}>
          <Text style={styles.title} numberOfLines={1}>
            {widget.title}
          </Text>
        </Pressable>
        <KebabStub />
      </View>
      <Pressable onPress={onOpen} style={styles.bodyHit}>
        <Text style={styles.ratio}>
          {count}
          <Text style={styles.goal}> / {target}</Text>
        </Text>
        {cue ? (
          <Text style={styles.cue} numberOfLines={3}>
            {cue.text}
          </Text>
        ) : null}
      </Pressable>
    </View>
  );
}

type TickTileProps = {
  widget: Widget;
  onToggle: () => void;
};

export function TickTile({ widget, onToggle }: TickTileProps) {
  const done = Boolean(widget.payload.done);
  return (
    <View style={styles.card}>
      <View style={styles.top}>
        <Pressable onPress={onToggle} style={styles.topHit}>
          <Text style={styles.title} numberOfLines={1}>
            {widget.title}
          </Text>
        </Pressable>
        <KebabStub />
      </View>
      <Pressable onPress={onToggle} style={styles.tickRow}>
        <View style={[styles.box, done && styles.boxDone]}>
          <Text style={[styles.check, done && styles.checkDone]}>{done ? '✓' : ''}</Text>
        </View>
        <Text style={styles.tickHint}>на Сегодня</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    padding: spacing.sm + 2,
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: 'space-between',
  },
  top: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: spacing.xs,
  },
  topHit: {
    flex: 1,
  },
  bodyHit: {
    flex: 1,
    justifyContent: 'flex-end',
    gap: spacing.xs,
  },
  title: {
    ...typography.subtitle,
    color: colors.text,
  },
  ratio: {
    fontSize: 28,
    fontWeight: '700',
    color: colors.text,
    letterSpacing: -0.6,
  },
  goal: {
    fontSize: 16,
    fontWeight: '600',
    color: colors.textSecondary,
  },
  cue: {
    ...typography.cue,
    color: colors.primary,
  },
  tickRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.xs,
  },
  box: {
    width: 36,
    height: 36,
    borderRadius: radii.sm,
    borderWidth: 2,
    borderColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.white,
  },
  boxDone: {
    backgroundColor: colors.primary,
  },
  check: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.primary,
  },
  checkDone: {
    color: colors.white,
  },
  tickHint: {
    ...typography.caption,
    color: colors.textMuted,
  },
});
