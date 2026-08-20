import Foundation

struct DayStrip: Sendable, Equatable, Identifiable {
    var date: Date
    var slots: [Slot]

    var id: TimeInterval { date.timeIntervalSinceReferenceDate }
}
