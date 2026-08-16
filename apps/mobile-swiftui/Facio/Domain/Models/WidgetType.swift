import Foundation

enum WidgetType: String, Codable, Sendable, Equatable {
    case counter
    case tick
    case checklist
    case reminder
    case timer
    case stepper

    var showsOnLid: Bool {
        switch self {
        case .counter, .tick, .reminder: true
        case .checklist, .timer, .stepper: false
        }
    }
}
