import Foundation

struct Slot: Sendable, Equatable, Identifiable {
    var subjectId: String
    var date: Date
    var kind: SlotKind
    /// `nil` means a cadence projection, not a desk instance.
    var instanceId: String?

    var id: String {
        "\(subjectId)|\(date.timeIntervalSinceReferenceDate)|\(instanceId ?? "proj")|\(kind.rawValue)"
    }
}
