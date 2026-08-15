import React from 'react';
import { StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { projectLid } from '@/domain/lid';
import { formatFireClock } from '@/domain/reminder';
import { cellsForTile, packRowMajor } from '@/domain/pack';
import type { Cue, Widget } from '@/domain/types';
import { colors, grid, spacing, typography } from '@/theme';
import { CounterTile, ReminderTile, TickTile } from './tiles';

type LidFeedProps = {
  widgets: Widget[];
  cueFor: (subjectId: string) => Cue | undefined;
  onOpenUse: (widgetId: string) => void;
  onToggleTick: (widgetId: string) => void;
  onCueSurfaced: (widgetId: string) => void;
  onOpenWindow: (widgetId: string) => void;
};

function SectionHeader({ title }: { title: string }) {
  return (
    <View style={styles.headerHit}>
      <Text style={styles.header}>{title}</Text>
    </View>
  );
}

function renderTile(
  item: Widget,
  props: Omit<LidFeedProps, 'widgets'>,
): React.ReactElement | null {
  switch (item.type) {
    case 'counter':
      return (
        <CounterTile
          widget={item}
          cue={props.cueFor(item.subject_id)}
          onOpen={() => props.onOpenUse(item.id)}
          onSurfaced={() => props.onCueSurfaced(item.id)}
        />
      );
    case 'tick':
      return (
        <TickTile
          widget={item}
          onOpen={() => props.onOpenUse(item.id)}
          onToggle={() => props.onToggleTick(item.id)}
        />
      );
    case 'reminder':
      return (
        <ReminderTile
          widget={item}
          fireClock={formatFireClock(item.payload.fire_at)}
          onOpen={() => props.onOpenUse(item.id)}
          onOpenWindow={() => props.onOpenWindow(item.id)}
        />
      );
    case 'checklist':
    case 'timer':
    case 'stepper':
      return null;
    default: {
      const exhaustive: never = item.type;
      return exhaustive;
    }
  }
}

function PackedSection({
  widgets,
  cueFor,
  onOpenUse,
  onToggleTick,
  onCueSurfaced,
  onOpenWindow,
}: {
  widgets: Widget[];
} & Omit<LidFeedProps, 'widgets'>) {
  const { width } = useWindowDimensions();
  const inner = width - grid.padding * 2;
  const cell = (inner - grid.gap * (grid.columns - 1)) / grid.columns;
  const { placements, rowCount } = packRowMajor(widgets, (widget) => cellsForTile(widget.tile_size));
  const height =
    rowCount > 0 ? rowCount * cell + Math.max(0, rowCount - 1) * grid.gap : 0;

  return (
    <View style={[styles.grid, { height }]}>
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
            {renderTile(item, {
              cueFor,
              onOpenUse,
              onToggleTick,
              onCueSurfaced,
              onOpenWindow,
            })}
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
  onOpenWindow,
}: LidFeedProps) {
  const lid = projectLid(widgets);

  return (
    <View style={styles.root}>
      <SectionHeader title="Сегодня" />
      {lid.today.length === 0 ? (
        <View style={styles.empty} />
      ) : (
        <PackedSection
          widgets={lid.today}
          cueFor={cueFor}
          onOpenUse={onOpenUse}
          onToggleTick={onToggleTick}
          onCueSurfaced={onCueSurfaced}
          onOpenWindow={onOpenWindow}
        />
      )}

      {lid.lifetime.length > 0 ? (
        <>
          <SectionHeader title="Lifetime" />
          <PackedSection
            widgets={lid.lifetime}
            cueFor={cueFor}
            onOpenUse={onOpenUse}
            onToggleTick={onToggleTick}
            onCueSurfaced={onCueSurfaced}
            onOpenWindow={onOpenWindow}
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
