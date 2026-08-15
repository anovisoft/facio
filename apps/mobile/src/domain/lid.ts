import type { RankBand, Widget, WidgetSection } from './types';

const HIDDEN_TODAY = new Set(['done', 'skipped', 'archived', 'snoozed']);

const BAND_ORDER: RankBand[] = [
  'in_progress',
  'overdue',
  'unanswered_morning',
  'drift_card',
  'soon_by_time',
  'today_incomplete',
];

export type LidView = {
  today: Widget[];
  lifetime: Widget[];
  soon: Widget[];
  postponed: Widget[];
};

function bandIndex(band: RankBand): number {
  return BAND_ORDER.indexOf(band);
}

export function widgetRankBand(widget: Widget, now: Date): RankBand {
  if (widget.status === 'running') return 'in_progress';
  if (widget.when) {
    const when = new Date(widget.when);
    if (when < now) return 'overdue';
    if (when.toDateString() === now.toDateString() && when > now) {
      return 'soon_by_time';
    }
  }
  return 'today_incomplete';
}

/**
 * Step-1 lid: widgets with section=today (and not idle-done) draw in Сегодня.
 * Drift cards stay in the law; they are not shown until step 3.
 */
export function projectLid(widgets: Widget[], now = new Date()): LidView {
  const today = widgets
    .filter((widget) => widget.section === 'today' && !HIDDEN_TODAY.has(widget.status))
    .slice()
    .sort((a, b) => {
      const band = bandIndex(widgetRankBand(a, now)) - bandIndex(widgetRankBand(b, now));
      if (band !== 0) return band;
      return a.id.localeCompare(b.id);
    });

  const bySection = (section: WidgetSection) =>
    widgets.filter((widget) => widget.section === section).sort((a, b) => a.id.localeCompare(b.id));

  return {
    today,
    lifetime: bySection('lifetime'),
    soon: bySection('soon'),
    postponed: bySection('postponed'),
  };
}
