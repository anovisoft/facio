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
    <Pressable onPress={onOpen} style={styles.card}>
      <View style={styles.top}>
        <Text style={styles.title} numberOfLines={1}>
          {widget.title}
        </Text>
        <KebabStub />
      </View>
      <View style={styles.bodyHit}>
        <Text style={styles.ratio}>
          {count}
          <Text style={styles.goal}> / {target}</Text>
        </Text>
        {cue ? (
          <Text style={styles.cue} numberOfLines={3}>
            {cue.text}
          </Text>
        ) : null}
      </View>
    </Pressable>
  );
}

type ReminderTileProps = {
  widget: Widget;
  fireClock: string;
  onOpen: () => void;
  onOpenWindow: () => void;
};

/** Row tile. Timing cue is the fire hour, not «зал до 22» as do-time text. */
export function ReminderTile({ widget, fireClock, onOpen, onOpenWindow }: ReminderTileProps) {
  return (
    <Pressable onPress={onOpen} style={styles.rowCard}>
      <View style={styles.rowCopy}>
        <Text style={styles.title} numberOfLines={1}>
          {widget.title}
        </Text>
        <Pressable
          onPress={onOpenWindow}
          style={({ pressed }) => [styles.clockHit, pressed && styles.pressed]}
          accessibilityLabel="во сколько напомнить"
        >
          <Text style={styles.fireClock}>{fireClock || '—'}</Text>
        </Pressable>
      </View>
      <KebabStub />
    </Pressable>
  );
}

type TickTileProps = {
  widget: Widget;
  onOpen: () => void;
  onToggle: () => void;
};

export function TickTile({ widget, onOpen, onToggle }: TickTileProps) {
  const done = Boolean(widget.payload.done);
  return (
    <Pressable onPress={onOpen} style={styles.card}>
      <View style={styles.top}>
        <Text style={styles.title} numberOfLines={1}>
          {widget.title}
        </Text>
        <KebabStub />
      </View>
      <View style={styles.tickRow}>
        <Pressable
          onPress={onToggle}
          style={({ pressed }) => [styles.box, done && styles.boxDone, pressed && styles.pressed]}
          accessibilityLabel="галочка"
        >
          <Text style={[styles.check, done && styles.checkDone]}>{done ? '✓' : ''}</Text>
        </Pressable>
        <Text style={styles.tickHint}>на Сегодня</Text>
      </View>
    </Pressable>
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
  bodyHit: {
    flex: 1,
    justifyContent: 'flex-end',
    gap: spacing.xs,
  },
  title: {
    ...typography.subtitle,
    color: colors.text,
    flex: 1,
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
    flex: 1,
  },
  rowCard: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radii.lg,
    paddingHorizontal: spacing.sm + 2,
    paddingVertical: spacing.xs,
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  rowCopy: {
    flex: 1,
    minWidth: 0,
    justifyContent: 'center',
  },
  clockHit: {
    alignSelf: 'flex-start',
    paddingVertical: 2,
  },
  fireClock: {
    fontSize: 20,
    fontWeight: '700',
    color: colors.primary,
    letterSpacing: -0.4,
  },
  pressed: {
    opacity: 0.7,
  },
});
