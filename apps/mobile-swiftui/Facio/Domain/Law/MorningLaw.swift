import Foundation

/// Port of `packages/domain/facio_domain/morning.py`.
///
/// The morning card fires on a delta or on drift, at most one, never both
/// (Q6, P8). Delta is the calm half: what this period promised minus what
/// actually got done. Drift is the loud half and wins when both are true —
/// saying the same thing twice in one morning is the nagging P8 rules out.
///
/// Nothing here invents a chore (never-do #15): every number comes from a
/// cadence the person named and instances they closed themselves.
enum MorningLaw {
    private static let done: Set<InstanceStatus> = [.completed]
    private static let liveToday: Set<WidgetStatus> = [.ready, .running]

    static func periodDays(for cadence: Cadence) -> Int? {
        if cadence.isNone { return nil }
        switch cadence.period {
        case .week: return 7
        case .day: return 1
        case .none: return nil
        }
    }

    static func promised(for cadence: Cadence) -> Int {
        cadence.isNone ? 0 : (cadence.count ?? 0)
    }

    /// Completed instances inside the trailing cadence period ending today.
    /// A trailing window, not a calendar week: cadence is a count per period
    /// (Q26), so Monday must not reset anybody's arithmetic.
    static func doneInPeriod(_ subject: Subject, instances: [Instance], now: Date) -> Int {
        guard let days = periodDays(for: subject.cadence) else { return 0 }
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: now)
        guard let start = calendar.date(byAdding: .day, value: -(days - 1), to: today) else { return 0 }
        return instances.filter { instance in
            guard instance.subjectId == subject.id, done.contains(instance.status) else { return false }
            let day = calendar.startOfDay(for: instance.when)
            return day >= start && day <= today
        }.count
    }

    /// Promised minus done, floored at zero. Doing more than promised is not a
    /// debt, so this never becomes a score to beat (P7).
    static func delta(_ subject: Subject, instances: [Instance], now: Date) -> Int {
        max(0, promised(for: subject.cadence) - doneInPeriod(subject, instances: instances, now: now))
    }

    /// At most one delta card: the biggest shortfall, largest id on a tie.
    static func deltaCard(
        subjects: [Subject],
        instances: [Instance],
        widgets: [Widget],
        now: Date
    ) -> DeltaCard? {
        let rows: [(remaining: Int, id: String, subject: Subject)] = subjects.compactMap { subject in
            guard subject.status != .retired, subject.status != .paused else { return nil }
            // A practice that has never run once owes nothing. Drift refuses to
            // fire on a subject with no activity and the delta follows the same
            // line: a rhythm nobody has started is a plan, and billing it on day
            // one is inventing a chore (never-do #15).
            guard DriftLaw.lastActivity(of: subject, in: instances) != nil else { return nil }
            guard !DriftLaw.isDrifting(subject, instances: instances, now: now) else { return nil }
            guard !hasLiveTileToday(subject, widgets: widgets) else { return nil }
            let remaining = delta(subject, instances: instances, now: now)
            guard remaining > 0 else { return nil }
            return (remaining, subject.id, subject)
        }
        guard let top = rows.max(by: { lhs, rhs in
            if lhs.remaining != rhs.remaining { return lhs.remaining < rhs.remaining }
            return lhs.id < rhs.id
        }) else { return nil }
        return DeltaCard(
            subjectId: top.subject.id,
            promised: promised(for: top.subject.cadence),
            done: doneInPeriod(top.subject, instances: instances, now: now),
            remaining: top.remaining
        )
    }

    /// If the practice is already sitting on Today, the tile *is* the delta
    /// made physical, and a card repeating it would be a second inventory of
    /// the same commitment (P10).
    private static func hasLiveTileToday(_ subject: Subject, widgets: [Widget]) -> Bool {
        widgets.contains { widget in
            widget.subjectId == subject.id
                && widget.section == .today
                && liveToday.contains(widget.status)
        }
    }
}
