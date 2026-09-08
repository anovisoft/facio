import Foundation

enum SubjectLaw {
    /// «через два дня» — two calendar days, at the hour the practice froze.
    static let pauseCheckInDays = 2

    static func shrink(_ subject: Subject) -> Subject {
        var next = subject
        next.status = .shrunk
        return next
    }

    static func retire(_ subject: Subject) -> Subject {
        var next = subject
        next.status = .retired
        return next
    }

    static func freeze(_ subject: Subject, now: Date) -> Subject {
        var next = subject
        next.status = .paused
        next.pausedAt = now
        return next
    }

    static func thaw(_ subject: Subject) -> Subject {
        var next = subject
        next.status = .active
        next.pausedAt = nil
        return next
    }

    /// Two **days** after the freeze, not 48 hours after it.
    ///
    /// `packages/domain` adds `timedelta(days=2)` to a wall clock, so a pause
    /// taken at 19:00 asks again at 19:00. Adding a fixed 172 800 seconds does
    /// not: on the two nights a year the clock moves, the two ports landed an
    /// hour apart — frozen at 19:00 on the Friday before the spring change, the
    /// phone asked «готов тренироваться?» at 20:00 on the Sunday.
    static func pauseCheckInAt(_ pausedAt: Date) -> Date {
        Calendar.current.date(byAdding: .day, value: pauseCheckInDays, to: pausedAt) ?? pausedAt
    }
}
