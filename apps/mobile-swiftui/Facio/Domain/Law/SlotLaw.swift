import Foundation

/// Cadence unfolded onto dates. Count per period, not weekdays (Q26).
enum SlotLaw {
    static let horizonLength = 7

    private static let open: Set<InstanceStatus> = [.prepared, .inProgress]

    /// Gregorian day math in the device time zone. POSIX locale so names never leak.
    /// `weekday` is Sunday=1…Saturday=7 on this calendar; ISO Monday=0 is derived
    /// from that number. Do not read `firstWeekday` — locale would break Q26.
    static var dayCalendar: Calendar {
        var calendar = Calendar(identifier: .gregorian)
        calendar.locale = Locale(identifier: "en_US_POSIX")
        calendar.timeZone = .current
        return calendar
    }

    static func horizon(desk: DeskSnapshot, origin: Date) -> Horizon {
        horizon(subjects: desk.subjects, instances: desk.instances, origin: origin)
    }

    static func horizon(subjects: [Subject], instances: [Instance], origin: Date) -> Horizon {
        let calendar = dayCalendar
        let originDay = startOfDay(for: origin, calendar: calendar)
        guard let last = calendar.date(byAdding: .day, value: horizonLength - 1, to: originDay) else {
            return Horizon(days: [], later: [])
        }
        let dayDates = (0..<horizonLength).compactMap { offset in
            calendar.date(byAdding: .day, value: offset, to: originDay)
        }
        var slotsByDay: [Date: [Slot]] = Dictionary(uniqueKeysWithValues: dayDates.map { ($0, []) })

        for instance in instances {
            let day = startOfDay(for: instance.when, calendar: calendar)
            if day >= originDay, day <= last {
                slotsByDay[day, default: []].append(realSlot(instance, day: day))
            }
        }

        let bySubject = instancesBySubject(instances)
        for subject in subjects {
            let owned = bySubject[subject.id] ?? []
            for slot in projections(subject, instances: owned, origin: originDay, last: last, calendar: calendar) {
                slotsByDay[slot.date, default: []].append(slot)
            }
        }

        let later = laterDays(in: instances, after: last, calendar: calendar)
        return Horizon(
            days: dayDates.map { DayStrip(date: $0, slots: slotsByDay[$0] ?? []) },
            later: later
        )
    }

    /// How many occurrences this practice owes on one calendar day (Q34).
    ///
    /// Only a rhythm counted **per day** can owe more than one on a given date:
    /// a weekly count spreads over the week's dates and the projection decides
    /// which ones. Retired, paused and `none` owe nothing — that is not
    /// silence, it is a practice that is not asking today.
    static func occurrencesPromised(_ subject: Subject) -> Int {
        if subject.status == .retired || subject.status == .paused { return 0 }
        guard subject.cadence.period == .day, let count = subject.cadence.count else { return 0 }
        return count
    }

    /// How many occurrences are still missing from `day`.
    ///
    /// Counts every case already standing on that date, **completed ones
    /// included**: the seventh check is the seventh case, so ticking the first
    /// must not make an eighth appear (04, Q34). Nothing is carried in from
    /// yesterday — the rest of a period is not the next period's debt.
    ///
    /// A reminder's own case does not count. The hours live in the subject's
    /// window, not one event per hour (Q34), so the case a reminder tile stands
    /// on is the hour itself — counting it would silently eat one of the checks.
    static func occurrencesMissing(
        _ subject: Subject,
        instances: [Instance],
        widgets: [Widget],
        on day: Date
    ) -> Int {
        let promised = occurrencesPromised(subject)
        guard promised > 0 else { return 0 }
        let calendar = dayCalendar
        let target = startOfDay(for: day, calendar: calendar)
        let hours = Set(
            widgets.filter { $0.subjectId == subject.id && $0.type == .reminder }.map(\.instanceId)
        )
        let standing = instances.filter {
            $0.subjectId == subject.id
                && startOfDay(for: $0.when, calendar: calendar) == target
                && !hours.contains($0.id)
        }.count
        return max(0, promised - standing)
    }

    static func startOfDay(for date: Date) -> Date {
        startOfDay(for: date, calendar: dayCalendar)
    }

    static func isSameDay(_ lhs: Date, _ rhs: Date) -> Bool {
        let calendar = dayCalendar
        return startOfDay(for: lhs, calendar: calendar) == startOfDay(for: rhs, calendar: calendar)
    }

    static func dayKey(_ date: Date) -> String {
        let parts = dayCalendar.dateComponents([.year, .month, .day], from: date)
        let year = parts.year ?? 0
        let month = parts.month ?? 0
        let day = parts.day ?? 0
        return String(format: "%04d-%02d-%02d", year, month, day)
    }

    /// Monday=0 … Sunday=6, matching Python `datetime.date.weekday()`.
    static func isoWeekdayMondayZero(_ date: Date) -> Int {
        isoWeekdayMondayZero(date, calendar: dayCalendar)
    }

    private static func startOfDay(for date: Date, calendar: Calendar) -> Date {
        calendar.startOfDay(for: date)
    }

    /// Gregorian `weekday` is Sunday=1 … Saturday=7, independent of `firstWeekday`.
    private static func isoWeekdayMondayZero(_ date: Date, calendar: Calendar) -> Int {
        let sundayBased = calendar.component(.weekday, from: date)
        return (sundayBased + 5) % 7
    }

    private static func realSlot(_ instance: Instance, day: Date) -> Slot {
        let kind: SlotKind = instance.status == .completed ? .done : .due
        return Slot(subjectId: instance.subjectId, date: day, kind: kind, instanceId: instance.id)
    }

    private static func instancesBySubject(_ instances: [Instance]) -> [String: [Instance]] {
        var grouped: [String: [Instance]] = [:]
        for instance in instances {
            grouped[instance.subjectId, default: []].append(instance)
        }
        return grouped
    }

    private static func projections(
        _ subject: Subject,
        instances: [Instance],
        origin: Date,
        last: Date,
        calendar: Calendar
    ) -> [Slot] {
        if subject.status == .retired || subject.status == .paused { return [] }
        let cadence = subject.cadence
        switch cadence.period {
        case .none:
            return []
        case .day, .week:
            guard let count = cadence.count else { return [] }
            var projected: [Slot] = []
            for (start, end) in periodsTouching(origin: origin, last: last, period: cadence.period, calendar: calendar) {
                projected.append(
                    contentsOf: periodProjections(
                        subjectId: subject.id,
                        count: count,
                        instances: instances,
                        periodStart: start,
                        periodEnd: end,
                        origin: origin,
                        last: last,
                        calendar: calendar
                    )
                )
            }
            return projected
        }
    }

    private static func periodProjections(
        subjectId: String,
        count: Int,
        instances: [Instance],
        periodStart: Date,
        periodEnd: Date,
        origin: Date,
        last: Date,
        calendar: Calendar
    ) -> [Slot] {
        let inPeriod = instances.filter { instance in
            let day = startOfDay(for: instance.when, calendar: calendar)
            return day >= periodStart && day <= periodEnd
        }
        let completedN = inPeriod.filter { $0.status == .completed }.count
        let openN = inPeriod.filter { open.contains($0.status) }.count
        let toProject = max(0, count - completedN - openN)
        if periodStart == periodEnd {
            // The period is one calendar day, so every occurrence it still owes
            // lands on that same day (Q34). Seven checks promised for today are
            // seven slots on today — not one, and not one a day for a week: the
            // count belongs to the period, and this period is over at midnight.
            guard periodStart >= origin, periodStart <= last else { return [] }
            return (0..<toProject).map { _ in
                Slot(subjectId: subjectId, date: periodStart, kind: .due, instanceId: nil)
            }
        }
        let occupied = Set(inPeriod.map { startOfDay(for: $0.when, calendar: calendar) })
        var candidates: [Date] = []
        var day = periodStart
        while day <= periodEnd {
            if day >= origin, day <= last, !occupied.contains(day) {
                candidates.append(day)
            }
            guard let next = calendar.date(byAdding: .day, value: 1, to: day) else { break }
            day = next
        }
        return candidates.prefix(toProject).map { candidate in
            Slot(subjectId: subjectId, date: candidate, kind: .due, instanceId: nil)
        }
    }

    private static func periodsTouching(
        origin: Date,
        last: Date,
        period: CadencePeriod,
        calendar: Calendar
    ) -> [(Date, Date)] {
        var spans: [(Date, Date)] = []
        var cursor = origin
        while cursor <= last {
            let span = periodSpan(cursor, period: period, calendar: calendar)
            spans.append(span)
            guard let next = calendar.date(byAdding: .day, value: 1, to: span.1) else { break }
            cursor = next
        }
        return spans
    }

    private static func periodSpan(_ day: Date, period: CadencePeriod, calendar: Calendar) -> (Date, Date) {
        let start = startOfDay(for: day, calendar: calendar)
        switch period {
        case .none:
            return (start, start)
        case .day:
            return (start, start)
        case .week:
            let mondayZero = isoWeekdayMondayZero(start, calendar: calendar)
            let weekStart = calendar.date(byAdding: .day, value: -mondayZero, to: start) ?? start
            let weekEnd = calendar.date(byAdding: .day, value: 6, to: weekStart) ?? start
            return (weekStart, weekEnd)
        }
    }

    private static func laterDays(in instances: [Instance], after last: Date, calendar: Calendar) -> [Date] {
        var seen: Set<Date> = []
        var later: [Date] = []
        for instance in instances {
            let day = startOfDay(for: instance.when, calendar: calendar)
            if day > last, seen.insert(day).inserted {
                later.append(day)
            }
        }
        return later.sorted()
    }
}
