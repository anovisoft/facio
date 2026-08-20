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
        widgets: [Widget],
        histories: [String: DriftAskState] = [:]
    ) -> LidProjection {
        let card = DriftLaw.driftCard(subjects: subjects, instances: instances, now: now, histories: histories)
        let visible = withoutPaused(subjects: subjects, widgets: widgets)
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
        }
        today.sort { lhs, rhs in
            sortKey(lhs, now: now) < sortKey(rhs, now: now)
        }

        return LidProjection(
            today: today,
            lifetime: lifetime,
            soon: soon,
            postponed: postponed,
            driftCard: card
        )
    }

    private static func withoutPaused(subjects: [Subject], widgets: [Widget]) -> [Widget] {
        let paused = Set(subjects.filter { $0.status == .paused }.map(\.id))
        return widgets.filter { !paused.contains($0.subjectId) }
    }

    private static func isDoneToday(_ widget: Widget, now: Date) -> Bool {
        guard widget.status == .done, let when = widget.when else { return false }
        return Calendar.current.isDate(when, inSameDayAs: now)
    }

    private static func todayWidgets(from widgets: [Widget], now: Date) -> [Widget] {
        var seen = Set<String>()
        var chosen: [Widget] = []
        for widget in widgets {
            if hiddenToday.contains(widget.status) { continue }
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
        case .widget(let band, let widget):
            return (band.sortIndex, widget.when ?? now, widget.id)
        }
    }
}
