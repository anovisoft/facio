import Foundation

enum SubjectLaw {
    static let pauseCheckIn: TimeInterval = 2 * 24 * 60 * 60

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

    static func pauseCheckInAt(_ pausedAt: Date) -> Date {
        pausedAt.addingTimeInterval(pauseCheckIn)
    }
}
