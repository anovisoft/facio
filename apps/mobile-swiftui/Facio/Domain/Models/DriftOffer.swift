import Foundation

enum DriftOffer: String, Codable, Sendable, Equatable {
    case moveToToday = "move_to_today"
    case onceAWeek = "once_a_week"
    case retire
    case stop
}
