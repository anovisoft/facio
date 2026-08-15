import React, { useCallback } from 'react';
import { Pressable, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { projectLid } from '@/domain/lid';
import { cellsForTile, packRowMajor } from '@/domain/pack';
import type { Cue, Widget } from '@/domain/types';
import { colors, grid, spacing, typography } from '@/theme';
import { CounterTile, TickTile } from './tiles';

type LidFeedProps = {
  widgets: Widget[];
  cueFor: (subjectId: string) => Cue | undefined;
  onOpenUse: (widgetId: string) => void;
  onToggleTick: (widgetId: string) => void;
  onCueSurfaced: (widgetId: string) => void;
};

function SectionHeader({
  title,
  onPress,
}: {
  title: string;
  onPress?: () => void;
}) {
  return (
    <Pressable onPress={onPress} disabled={!onPress} style={styles.headerHit}>
      <Text style={styles.header}>{title}</Text>
    </Pressable>
  );
}

function PackedSection({
  widgets,
  cueFor,
  onOpenUse,
  onToggleTick,
  onCueSurfaced,
  onEmptyPress,
}: {
  widgets: Widget[];
  onEmptyPress?: () => void;
} & Omit<LidFeedProps, 'widgets'>) {
  const { width } = useWindowDimensions();
  const inner = width - grid.padding * 2;
  const cell = (inner - grid.gap * (grid.columns - 1)) / grid.columns;
  const { placements, rowCount } = packRowMajor(widgets, (widget) => cellsForTile(widget.tile_size));
  const height =
    rowCount > 0 ? rowCount * cell + Math.max(0, rowCount - 1) * grid.gap : 0;

  return (
    <View style={[styles.grid, { height }]}>
      {onEmptyPress ? (
        <Pressable style={StyleSheet.absoluteFill} onPress={onEmptyPress} />
      ) : null}
      {placements.map(({ item, col, row, w, h }) => {
        const left = col * (cell + grid.gap);
        const top = row * (cell + grid.gap);
        const tileWidth = w * cell + (w - 1) * grid.gap;
        const tileHeight = h * cell + (h - 1) * grid.gap;
        return (
          <View
            key={item.id}
            style={[
              styles.slot,
              { left, top, width: tileWidth, height: tileHeight },
            ]}
          >
            {item.type === 'counter' ? (
              <CounterTile
                widget={item}
                cue={cueFor(item.subject_id)}
                onOpen={() => onOpenUse(item.id)}
                onSurfaced={() => onCueSurfaced(item.id)}
              />
            ) : item.type === 'tick' ? (
              <TickTile widget={item} onToggle={() => onToggleTick(item.id)} />
            ) : null}
          </View>
        );
      })}
    </View>
  );
}

export function LidFeed({
  widgets,
  cueFor,
  onOpenUse,
  onToggleTick,
  onCueSurfaced,
}: LidFeedProps) {
  const lid = projectLid(widgets);
  const firstCounter = lid.today.find((widget) => widget.type === 'counter');
  const openFirstCounter = useCallback(() => {
    if (firstCounter) onOpenUse(firstCounter.id);
  }, [firstCounter, onOpenUse]);

  return (
    <View style={styles.root}>
      <SectionHeader title="Сегодня" onPress={openFirstCounter} />
      {lid.today.length === 0 ? (
        <View style={styles.empty} />
      ) : (
        <PackedSection
          widgets={lid.today}
          cueFor={cueFor}
          onOpenUse={onOpenUse}
          onToggleTick={onToggleTick}
          onCueSurfaced={onCueSurfaced}
          onEmptyPress={openFirstCounter}
        />
      )}

      {lid.lifetime.length > 0 ? (
        <>
          <SectionHeader
            title="Lifetime"
            onPress={() => {
              const first = lid.lifetime.find((widget) => widget.type === 'counter');
              if (first) onOpenUse(first.id);
            }}
          />
          <PackedSection
            widgets={lid.lifetime}
            cueFor={cueFor}
            onOpenUse={onOpenUse}
            onToggleTick={onToggleTick}
            onCueSurfaced={onCueSurfaced}
          />
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    paddingHorizontal: grid.padding,
    paddingBottom: spacing.xl,
  },
  headerHit: {
    paddingTop: spacing.lg,
    paddingBottom: spacing.sm,
  },
  header: {
    ...typography.title,
    color: colors.text,
  },
  grid: {
    position: 'relative',
    width: '100%',
  },
  slot: {
    position: 'absolute',
  },
  empty: {
    height: spacing.sm,
  },
});
