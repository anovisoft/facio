import Foundation

enum DriftOffer: String, Codable, Sendable, Equatable, Hashable, CaseIterable {
    case moveToToday = "move_to_today"
    case onceAWeek = "once_a_week"
    case retire
    case stop

    /// The ladder in order, least drastic first. Only one of these is on the
    /// card at a time — `DriftLaw.nextOffer` picks the rung. Kept as a list so
    /// a test can assert the order never turns into “try harder” (never-do #21).
    static let ladder: [DriftOffer] = [.moveToToday, .onceAWeek, .retire]
}
