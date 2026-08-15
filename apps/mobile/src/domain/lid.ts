import { driftCard } from './drift';
import { formatLocalDate, parseWhen, sameCalendarDay } from './reminder';
import type {
  DriftCard,
  Instance,
  RankBand,
  Subject,
  Widget,
  WidgetSection,
} from './types';

const HIDDEN_TODAY = new Set(['skipped', 'archived', 'snoozed']);

const BAND_ORDER: RankBand[] = [
  'in_progress',
  'overdue',
  'unanswered_morning',
  'drift_card',
  'soon_by_time',
  'today_incomplete',
  'today_done',
];

export type WidgetTodayItem = {
  kind: 'widget';
  band: RankBand;
  widget: Widget;
};

export type DriftTodayItem = {
  kind: 'drift';
  band: 'drift_card';
  drift_card: DriftCard;
};

export type DeltaTodayItem = {
  kind: 'delta';
  band: 'unanswered_morning';
  widget_id: string;
  subject_id: string;
};

export type TodayItem = WidgetTodayItem | DriftTodayItem | DeltaTodayItem;

export type LidView = {
  today: TodayItem[];
  lifetime: Widget[];
  soon: Widget[];
  postponed: Widget[];
  drift_card: DriftCard | null;
  delta_card: DeltaTodayItem | null;
};

function bandIndex(band: RankBand): number {
  return BAND_ORDER.indexOf(band);
}

export function isDoneToday(widget: Widget, now: Date): boolean {
  if (widget.status !== 'done' || !widget.when) return false;
  return sameCalendarDay(parseWhen(widget.when), now);
}

export function widgetRankBand(widget: Widget, now: Date): RankBand {
  if (widget.status === 'done') return 'today_done';
  if (widget.status === 'running') return 'in_progress';
  if (widget.when) {
    const when = parseWhen(widget.when);
    if (when < now) return 'overdue';
    if (sameCalendarDay(when, now) && when > now) return 'soon_by_time';
  }
  return 'today_incomplete';
}

function todayWidgets(widgets: Widget[], now: Date): Widget[] {
  const seen = new Set<string>();
  const chosen: Widget[] = [];
  for (const widget of widgets) {
    if (HIDDEN_TODAY.has(widget.status)) continue;
    if (widget.status === 'done') {
      if (!isDoneToday(widget, now)) continue;
    } else if (widget.section !== 'today') {
      continue;
    }
    if (seen.has(widget.id)) continue;
    seen.add(widget.id);
    chosen.push(widget);
  }
  return chosen;
}

function sortKey(item: TodayItem, now: Date): [number, number, string] {
  if (item.kind === 'drift') {
    return [bandIndex('drift_card'), 0, item.drift_card.subject_id];
  }
  if (item.kind === 'delta') {
    return [bandIndex('unanswered_morning'), 0, item.subject_id];
  }
  const when = item.widget.when ? parseWhen(item.widget.when).getTime() : now.getTime();
  return [bandIndex(item.band), when, item.widget.id];
}

/**
 * One overdue Today widget and no drift → a quiet delta card.
 * Two reasons, or none → no card. Do not invent chores.
 */
export function deltaCard(
  widgets: Widget[],
  now: Date,
  morningClosedOn: string | null,
): DeltaTodayItem | null {
  if (morningClosedOn === formatLocalDate(now)) return null;
  const reasons = widgets.filter((widget) => {
    if (widget.section !== 'today') return false;
    if (widget.status === 'done' || HIDDEN_TODAY.has(widget.status)) return false;
    if (!widget.when) return false;
    return parseWhen(widget.when) < now;
  });
  if (reasons.length !== 1) return null;
  const widget = reasons[0];
  return {
    kind: 'delta',
    band: 'unanswered_morning',
    widget_id: widget.id,
    subject_id: widget.subject_id,
  };
}

export function projectLid(
  widgets: Widget[],
  subjects: Subject[] = [],
  instances: Instance[] = [],
  now = new Date(),
  morningClosedOn: string | null = null,
): LidView {
  const card = driftCard(subjects, instances, now);
  const onToday = todayWidgets(widgets, now);
  const today: TodayItem[] = onToday.map((widget) => ({
    kind: 'widget',
    band: widgetRankBand(widget, now),
    widget,
  }));

  let delta: DeltaTodayItem | null = null;
  if (card) {
    today.push({ kind: 'drift', band: 'drift_card', drift_card: card });
  } else {
    delta = deltaCard(widgets, now, morningClosedOn);
    if (delta) today.push(delta);
  }

  today.sort((a, b) => {
    const left = sortKey(a, now);
    const right = sortKey(b, now);
    if (left[0] !== right[0]) return left[0] - right[0];
    if (left[1] !== right[1]) return left[1] - right[1];
    return left[2].localeCompare(right[2]);
  });

  const todayIds = new Set(onToday.map((widget) => widget.id));
  const bySection = (section: WidgetSection) =>
    widgets
      .filter(
        (widget) =>
          widget.section === section &&
          widget.status !== 'done' &&
          !todayIds.has(widget.id),
      )
      .sort((a, b) => a.id.localeCompare(b.id));

  return {
    today,
    lifetime: bySection('lifetime'),
    soon: bySection('soon'),
    postponed: bySection('postponed'),
    drift_card: card,
    delta_card: delta,
  };
}
