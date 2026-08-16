import Foundation

enum ReminderClock {
    static let closingLeadHours = 3
    /// Picker floor when `Window` has no open. Not a stored field.
    static let defaultGymOpens = ClockTime(hour: 6, minute: 0)

    static func windowFromClosing(_ closesAt: ClockTime) -> TimeWindow {
        var latestHour = closesAt.hour - closingLeadHours
        if latestHour < 0 { latestHour += 24 }
        return TimeWindow(
            latestBy: ClockTime(hour: latestHour, minute: closesAt.minute, second: closesAt.second),
            closesAt: closesAt
        )
    }

    static func reminderFireAt(window: TimeWindow, on day: Date) -> Date {
        Self.date(on: day, clock: window.latestBy)
    }

    static func date(on day: Date, clock: ClockTime) -> Date {
        var parts = Calendar.current.dateComponents([.year, .month, .day], from: day)
        parts.hour = clock.hour
        parts.minute = clock.minute
        parts.second = clock.second
        return Calendar.current.date(from: parts) ?? day
    }

    static func clock(from date: Date) -> ClockTime {
        let parts = Calendar.current.dateComponents([.hour, .minute, .second], from: date)
        return ClockTime(hour: parts.hour ?? 0, minute: parts.minute ?? 0, second: parts.second ?? 0)
    }

    static func gymHours(window: TimeWindow, on day: Date) -> ClosedRange<Date> {
        let opens = defaultGymOpens
        let closes = window.closesAt ?? ClockTime(hour: 23, minute: 59)
        let start = date(on: day, clock: min(opens, closes))
        let end = date(on: day, clock: max(opens, closes))
        return start...end
    }

    static func gymHourRange(window: TimeWindow) -> ClosedRange<Int> {
        let opens = defaultGymOpens.hour
        let closes = window.closesAt?.hour ?? 23
        return min(opens, closes)...max(opens, closes)
    }

    static func clamp(_ clock: ClockTime, to window: TimeWindow) -> ClockTime {
        let day = date(on: Date(timeIntervalSinceReferenceDate: 0), clock: ClockTime(hour: 12, minute: 0))
        let range = gymHours(window: window, on: day)
        let candidate = date(on: day, clock: clock)
        let clamped = min(max(candidate, range.lowerBound), range.upperBound)
        return self.clock(from: clamped)
    }
}
