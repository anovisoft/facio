import React from 'react';
import { StyleSheet, Text, useWindowDimensions, View } from 'react-native';

import { deltaCardText, displayTitle, driftCardText } from '@/domain/copy';
import { projectLid, type TodayItem } from '@/domain/lid';
import { formatFireClock } from '@/domain/reminder';
import { cellsForTile, packRowMajor, type CellSize } from '@/domain/pack';
import type { Cue, Instance, Subject, Widget } from '@/domain/types';
import { colors, grid, spacing, typography } from '@/theme';
import { AskCard } from './AskCard';
import { CounterTile, ReminderTile, TickTile } from './tiles';

type LidFeedProps = {
  widgets: Widget[];
  subjects: Subject[];
  instances: Instance[];
  morningClosedOn: string | null;
  cueFor: (subjectId: string) => Cue | undefined;
  onOpenUse: (widgetId: string) => void;
  onToggleTick: (widgetId: string) => void;
  onCueSurfaced: (widgetId: string) => void;
  onOpenWindow: (widgetId: string) => void;
  onAnswerDrift: (subjectId: string, action: 'today' | 'weekly' | 'retire') => void;
  onAnswerDelta: (widgetId: string, action: 'yes' | 'leave' | 'later') => void;
};

function SectionHeader({ title }: { title: string }) {
  return (
    <View style={styles.headerHit}>
      <Text style={styles.header}>{title}</Text>
    </View>
  );
}

function sizeOfItem(item: TodayItem | Widget): CellSize {
  if ('kind' in item) {
    if (item.kind === 'drift' || item.kind === 'delta') return { w: 4, h: 2 };
    return cellsForTile(item.widget.tile_size);
  }
  return cellsForTile(item.tile_size);
}

function renderWidget(
  item: Widget,
  props: Omit<LidFeedProps, 'widgets' | 'subjects' | 'instances' | 'morningClosedOn'>,
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

function renderTodayItem(
  item: TodayItem,
  subjects: Subject[],
  props: Omit<LidFeedProps, 'widgets' | 'subjects' | 'instances' | 'morningClosedOn'>,
): React.ReactElement | null {
  switch (item.kind) {
    case 'widget':
      return renderWidget(item.widget, props);
    case 'drift': {
      const subject = subjects.find((row) => row.id === item.drift_card.subject_id);
      return (
        <AskCard
          text={driftCardText(displayTitle(subject), item.drift_card.silent_days)}
          chips={[
            {
              id: 'today',
              label: 'На сегодня',
              onPress: () => props.onAnswerDrift(item.drift_card.subject_id, 'today'),
            },
            {
              id: 'weekly',
              label: 'Раз в неделю',
              onPress: () => props.onAnswerDrift(item.drift_card.subject_id, 'weekly'),
            },
            {
              id: 'retire',
              label: 'Убрать',
              onPress: () => props.onAnswerDrift(item.drift_card.subject_id, 'retire'),
            },
          ]}
        />
      );
    }
    case 'delta': {
      const subject = subjects.find((row) => row.id === item.subject_id);
      return (
        <AskCard
          text={deltaCardText(displayTitle(subject))}
          chips={[
            { id: 'yes', label: 'Да', onPress: () => props.onAnswerDelta(item.widget_id, 'yes') },
            {
              id: 'leave',
              label: 'На сегодня',
              onPress: () => props.onAnswerDelta(item.widget_id, 'leave'),
            },
            {
              id: 'later',
              label: 'Позже',
              onPress: () => props.onAnswerDelta(item.widget_id, 'later'),
            },
          ]}
        />
      );
    }
    default: {
      const exhaustive: never = item;
      return exhaustive;
    }
  }
}

function PackedToday({
  items,
  subjects,
  ...props
}: {
  items: TodayItem[];
  subjects: Subject[];
} & Omit<LidFeedProps, 'widgets' | 'subjects' | 'instances' | 'morningClosedOn'>) {
  const { width } = useWindowDimensions();
  const inner = width - grid.padding * 2;
  const cell = (inner - grid.gap * (grid.columns - 1)) / grid.columns;
  const { placements, rowCount } = packRowMajor(items, sizeOfItem);
  const height = rowCount > 0 ? rowCount * cell + Math.max(0, rowCount - 1) * grid.gap : 0;

  return (
    <View style={[styles.grid, { height }]}>
      {placements.map(({ item, col, row, w, h }, index) => {
        const left = col * (cell + grid.gap);
        const top = row * (cell + grid.gap);
        const tileWidth = w * cell + (w - 1) * grid.gap;
        const tileHeight = h * cell + (h - 1) * grid.gap;
        const key =
          item.kind === 'widget'
            ? item.widget.id
            : item.kind === 'drift'
              ? `drift:${item.drift_card.subject_id}`
              : `delta:${item.widget_id}`;
        return (
          <View key={key || String(index)} style={[styles.slot, { left, top, width: tileWidth, height: tileHeight }]}>
            {renderTodayItem(item, subjects, props)}
          </View>
        );
      })}
    </View>
  );
}

function PackedWidgets({
  widgets,
  ...props
}: {
  widgets: Widget[];
} & Omit<LidFeedProps, 'widgets' | 'subjects' | 'instances' | 'morningClosedOn'>) {
  const { width } = useWindowDimensions();
  const inner = width - grid.padding * 2;
  const cell = (inner - grid.gap * (grid.columns - 1)) / grid.columns;
  const { placements, rowCount } = packRowMajor(widgets, sizeOfItem);
  const height = rowCount > 0 ? rowCount * cell + Math.max(0, rowCount - 1) * grid.gap : 0;

  return (
    <View style={[styles.grid, { height }]}>
      {placements.map(({ item, col, row, w, h }) => {
        const left = col * (cell + grid.gap);
        const top = row * (cell + grid.gap);
        const tileWidth = w * cell + (w - 1) * grid.gap;
        const tileHeight = h * cell + (h - 1) * grid.gap;
        return (
          <View key={item.id} style={[styles.slot, { left, top, width: tileWidth, height: tileHeight }]}>
            {renderWidget(item, props)}
          </View>
        );
      })}
    </View>
  );
}

export function LidFeed({
  widgets,
  subjects,
  instances,
  morningClosedOn,
  ...props
}: LidFeedProps) {
  const lid = projectLid(widgets, subjects, instances, new Date(), morningClosedOn);

  return (
    <View style={styles.root}>
      <SectionHeader title="Сегодня" />
      {lid.today.length === 0 ? (
        <View style={styles.empty} />
      ) : (
        <PackedToday items={lid.today} subjects={subjects} {...props} />
      )}

      {lid.lifetime.length > 0 ? (
        <>
          <SectionHeader title="Lifetime" />
          <PackedWidgets widgets={lid.lifetime} {...props} />
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
