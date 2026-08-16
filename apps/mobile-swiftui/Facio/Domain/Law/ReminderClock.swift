import Foundation

enum ReminderClock {
    static let closingLeadHours = 3

    static func windowFromClosing(_ closesAt: ClockTime) -> TimeWindow {
        var latestHour = closesAt.hour - closingLeadHours
        if latestHour < 0 { latestHour += 24 }
        return TimeWindow(
            latestBy: ClockTime(hour: latestHour, minute: closesAt.minute, second: closesAt.second),
            closesAt: closesAt
        )
    }

    static func reminderFireAt(window: TimeWindow, on date: Date) -> Date {
        var parts = Calendar.current.dateComponents([.year, .month, .day], from: date)
        parts.hour = window.latestBy.hour
        parts.minute = window.latestBy.minute
        parts.second = window.latestBy.second
        return Calendar.current.date(from: parts) ?? date
    }
}
