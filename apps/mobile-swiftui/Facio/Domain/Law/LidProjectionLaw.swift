import Foundation

enum LidProjectionLaw {
    private static let hiddenToday: Set<WidgetStatus> = [.skipped, .archived, .snoozed]

    static func widgetRankBand(_ widget: Widget, now: Date) -> RankBand {
        if widget.status == .done { return .todayDone }
        if widget.status == .running { return .inProgress }
        if let when = widget.when, when < now { return .overdue }
        if let when = widget.when, Calendar.current.isDate(when, inSameDayAs: now), when > now {
            return .soonByTime
        }
        return .todayIncomplete
    }

    static func project(
        now: Date,
        subjects: [Subject],
        instances: [Instance],
        widgets: [Widget]
    ) -> LidProjection {
        // One morning card: a drift ask when a period was missed, otherwise
        // the calm delta line (Q6). Never both — the drift card carries the
        // same subject louder.
        let card = DriftLaw.driftCard(subjects: subjects, instances: instances, now: now)
        // The morning reads the desk, not the drawing: hiding a tile must not
        // wake a delta line that the tile itself was answering (Q6).
        let delta = card == nil
            ? MorningLaw.deltaCard(subjects: subjects, instances: instances, widgets: widgets, now: now)
            : nil
        let visible = withoutRepeatedReminders(
            now: now,
            subjects: subjects,
            instances: instances,
            widgets: withoutPaused(subjects: subjects, widgets: widgets)
        )
        let todayWidgets = todayWidgets(from: visible, now: now)
        let todayIds = Set(todayWidgets.map(\.id))
        let lifetime = visible
            .filter { $0.section == .lifetime && !todayIds.contains($0.id) && $0.status != .done }
            .sorted { $0.id < $1.id }
        let soon = visible.filter { $0.section == .soon }.sorted { $0.id < $1.id }
        let postponed = visible.filter { $0.section == .postponed }.sorted { $0.id < $1.id }

        var today: [TodayItem] = todayWidgets.map { widget in
            .widget(band: widgetRankBand(widget, now: now), widget: widget)
        }
        if let card {
            today.append(.drift(card: card))
        } else if let delta {
            today.append(.delta(card: delta))
        }
        today.sort { lhs, rhs in
            sortKey(lhs, now: now) < sortKey(rhs, now: now)
        }

        return LidProjection(
            today: today,
            lifetime: lifetime,
            soon: soon,
            postponed: postponed,
            driftCard: card,
            deltaCard: delta
        )
    }

    /// Whether this subject's reminder tile is a second copy of its group tile.
    ///
    /// One practice, one promise, one tile. When today's group already carries
    /// the hours the window states, the reminder repeats it word for word —
    /// `15:30` large, `18:00 22:00` small — and the lid stops being a view of
    /// what is due now (P10).
    ///
    /// Only today's group counts, and only a group of more than one: a practice
    /// that promises once a day is never stamped, so a desk written before Q34
    /// draws exactly as it always did.
    static func reminderShadowedByGroup(
        subject: Subject,
        widgets: [Widget],
        instances: [Instance],
        now: Date
    ) -> Bool {
        guard let face = GroupLaw.face(
            of: GroupLaw.key(subjectId: subject.id, day: now),
            widgets: widgets,
            instances: instances,
            now: now
        ), face.total > 1 else { return false }
        return GroupLaw.saysEveryHour(face, window: subject.window)
    }

    /// Drop the reminder tile of a subject whose group already speaks its hours.
    ///
    /// A drawing rule and nothing else. The widget stays on the desk, keeps its
    /// status and keeps ringing: `ReminderScheduler.alarms(from:)` reads the
    /// desk snapshot, never this projection, so a tile that is not drawn is not
    /// an alarm that was cancelled.
    private static func withoutRepeatedReminders(
        now: Date,
        subjects: [Subject],
        instances: [Instance],
        widgets: [Widget]
    ) -> [Widget] {
        let silent = Set(
            subjects
                .filter {
                    reminderShadowedByGroup(
                        subject: $0,
                        widgets: widgets,
                        instances: instances,
                        now: now
                    )
                }
                .map(\.id)
        )
        guard !silent.isEmpty else { return widgets }
        return widgets.filter { $0.type != .reminder || !silent.contains($0.subjectId) }
    }

    private static func withoutPaused(subjects: [Subject], widgets: [Widget]) -> [Widget] {
        let paused = Set(subjects.filter { $0.status == .paused }.map(\.id))
        return widgets.filter { !paused.contains($0.subjectId) }
    }

    private static func isDoneToday(_ widget: Widget, now: Date) -> Bool {
        guard widget.status == .done, let when = widget.when else { return false }
        return Calendar.current.isDate(when, inSameDayAs: now)
    }

    /// Whether this widget belongs to a day that is over (R19).
    ///
    /// A `group_id` names a subject **and a date**, so a widget carrying
    /// yesterday's id is one of yesterday's checks. Once the day rolls over,
    /// today has its own group and drawing the old one too would put two tiles
    /// of one practice on the lid (R17) and quietly hand yesterday's misses to
    /// today — and a miss belongs to the day it happened.
    ///
    /// A drawing rule and nothing else, on the same line R17 took: the widgets
    /// stay on the desk with their dates and their statuses untouched, the
    /// carousel still lists them, and drift and delta still count them. A
    /// widget with no `group_id` — every widget of a desk written before Q34,
    /// and every practice that promises once a day — is never touched by this.
    private static func belongsToAClosedDay(_ widget: Widget, now: Date) -> Bool {
        guard let groupId = widget.groupId else { return false }
        return groupId != GroupLaw.key(subjectId: widget.subjectId, day: now)
    }

    private static func todayWidgets(from widgets: [Widget], now: Date) -> [Widget] {
        var seen = Set<String>()
        var chosen: [Widget] = []
        for widget in widgets {
            if hiddenToday.contains(widget.status) { continue }
            if belongsToAClosedDay(widget, now: now) { continue }
            if widget.status == .done {
                if !isDoneToday(widget, now: now) { continue }
            } else if widget.section != .today {
                continue
            }
            if seen.contains(widget.id) { continue }
            seen.insert(widget.id)
            chosen.append(widget)
        }
        return chosen
    }

    private static func sortKey(_ item: TodayItem, now: Date) -> (Int, Date, String) {
        switch item {
        case .drift(let card):
            return (RankBand.driftCard.sortIndex, Date.distantPast, card.subjectId)
        case .delta(let card):
            return (RankBand.unansweredMorning.sortIndex, Date.distantPast, card.subjectId)
        case .widget(let band, let widget):
            return (band.sortIndex, widget.when ?? now, widget.id)
        }
    }
}
