import Foundation

enum SubjectLaw {
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
}
