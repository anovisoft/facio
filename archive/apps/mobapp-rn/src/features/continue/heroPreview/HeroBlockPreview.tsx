/**
 * Hero Preview — read-only fragment of Session Block state for Continue.
 * Not a shrunk Full Block: no toggles, Start, or plugin controls.
 * Data from ActionResponse / next_action only.
 * ≈min lives in the card footer (ContinueScreen), not here.
 */

import React from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useTranslation } from '../../../../node_modules/react-i18next';

import type { ActionResponse, StepperBeatResponse } from '@/api/types';
import { blockTypeLabel } from '@/features/continue/blockTypeLabel';
import { detectHeroBlockKind } from '@/features/continue/heroPreview/detectBlockKind';
import { formatClock } from '@/features/continue/heroPreview/formatEstimate';
import type { ColorPalette } from '@/theme';
import { spacing, typography } from '@/theme';

/** Prefer 3 items — shared ~2–3 line rhythm; avoid 5-item wrap chaos. */
const CHECKLIST_PREVIEW_MAX = 3;

type Props = {
  action: ActionResponse;
  colors: ColorPalette;
};

function sortedChecklist(action: ActionResponse) {
  return [...action.checklist_items].sort((a, b) => a.sort - b.sort);
}

function beatHint(beat: StepperBeatResponse, index: number, total: number): string {
  const parts: string[] = [`${index + 1}/${total}`];
  parts.push(beat.kind);
  if (beat.counter) {
    parts.push(`${beat.counter.current}/${beat.counter.target}`);
  } else if (beat.duration_sec != null && beat.duration_sec > 0) {
    parts.push(formatClock(beat.duration_sec));
  }
  return parts.join(' · ');
}

function ChecklistHero({
  action,
  colors,
}: {
  action: ActionResponse;
  colors: ColorPalette;
}) {
  const items = sortedChecklist(action);
  const preview = items.slice(0, CHECKLIST_PREVIEW_MAX);
  const done = items.filter((i) => i.done).length;
  const total = items.length;

  return (
    <View style={styles.body}>
      <View style={styles.checkCol}>
        {preview.map((item) => (
          <Text
            key={item.id}
            style={[styles.checkItem, { color: colors.textSecondary }]}
            numberOfLines={1}
          >
            {item.done ? '☑' : '☐'} {item.title}
          </Text>
        ))}
      </View>
      <Text style={[styles.progress, { color: colors.textMuted }]}>
        {done}/{total}
      </Text>
    </View>
  );
}

function StepperHero({
  action,
  colors,
}: {
  action: ActionResponse;
  colors: ColorPalette;
}) {
  const beats = action.stepper?.beats ?? [];
  const current = beats[0];
  if (!current) return null;
  return (
    <View style={styles.body}>
      <Text
        style={[styles.fragment, { color: colors.textSecondary }]}
        numberOfLines={1}
      >
        {beatHint(current, 0, beats.length)}
        {current.title ? ` · ${current.title}` : ''}
      </Text>
    </View>
  );
}

function TimelineHero({
  action,
  colors,
}: {
  action: ActionResponse;
  colors: ColorPalette;
}) {
  const { t } = useTranslation();
  const timeline = action.timeline;
  if (!timeline) return null;
  const markers = timeline.markers.length;
  const clock = formatClock(timeline.duration_sec);
  const markerLine =
    markers > 0
      ? t('continue.heroMarkers', { count: markers })
      : null;
  return (
    <View style={styles.body}>
      <Text
        style={[styles.fragment, { color: colors.textSecondary }]}
        numberOfLines={1}
      >
        {markerLine ? `${clock} · ${markerLine}` : clock}
      </Text>
    </View>
  );
}

function TimerHero({
  action,
  colors,
}: {
  action: ActionResponse;
  colors: ColorPalette;
}) {
  const { t } = useTranslation();
  const timers = action.timers;
  if (timers.length === 0) return null;
  const first = timers[0];
  const clock = formatClock(first.duration_sec);
  const more =
    timers.length > 1
      ? t('continue.heroTimers', { count: timers.length })
      : first.title;
  return (
    <View style={styles.body}>
      <Text
        style={[styles.fragment, { color: colors.textSecondary }]}
        numberOfLines={1}
      >
        {clock}
        {more ? ` · ${more}` : ''}
      </Text>
    </View>
  );
}

function FallbackHero({
  action,
  colors,
}: {
  action: ActionResponse;
  colors: ColorPalette;
}) {
  const label = blockTypeLabel(action);
  if (!label) return null;
  return (
    <View style={styles.body}>
      <Text
        style={[styles.fragment, { color: colors.textSecondary }]}
        numberOfLines={1}
      >
        {label}
      </Text>
    </View>
  );
}

/**
 * Read-only Hero body under the Session title.
 * Parent owns title / Focus chip / footer (≈min + Guide grit) / Pressable → Session.
 */
export function HeroBlockPreview({ action, colors }: Props) {
  const kind = detectHeroBlockKind(action);

  let body: React.ReactNode = null;
  switch (kind) {
    case 'checklist':
      body = <ChecklistHero action={action} colors={colors} />;
      break;
    case 'stepper':
      body = <StepperHero action={action} colors={colors} />;
      break;
    case 'timeline':
      body = <TimelineHero action={action} colors={colors} />;
      break;
    case 'timer':
      body = <TimerHero action={action} colors={colors} />;
      break;
    case 'fallback':
      body = <FallbackHero action={action} colors={colors} />;
      break;
    default: {
      const _exhaustive: never = kind;
      return _exhaustive;
    }
  }

  return <View>{body}</View>;
}

const styles = StyleSheet.create({
  body: {
    marginTop: spacing.xs,
    gap: 2,
  },
  checkCol: {
    gap: 2,
  },
  checkItem: {
    ...typography.caption,
  },
  progress: {
    ...typography.label,
    marginTop: 2,
  },
  fragment: {
    ...typography.caption,
  },
});
