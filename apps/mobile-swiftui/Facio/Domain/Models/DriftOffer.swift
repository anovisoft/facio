import Foundation

enum DriftOffer: String, Codable, Sendable, Equatable, Hashable, CaseIterable {
    case moveToToday = "move_to_today"
    case onceAWeek = "once_a_week"
    case retire
    case stop

    /// Chips that only shrink commitment. Never “try harder”.
    static let downward: [DriftOffer] = [.moveToToday, .onceAWeek, .retire]
}
