import Foundation

enum WidgetType: String, Codable, Sendable, Equatable {
    case counter
    case tick
    case checklist
    case reminder
    case timer
    case stepper

    /// A type is on the lid only once it has a runtime on both sides. The
    /// gate lifts per type, together with that runtime — a type with nowhere
    /// to run would land on the lid and vanish (В1.1, never-do #14). Every
    /// catalog type has one now; a new type arrives here as `false`.
    var showsOnLid: Bool {
        switch self {
        case .counter, .tick, .reminder, .checklist, .timer, .stepper: true
        }
    }

    /// May the tile itself be worked, or does it only open Use? The stepper's
    /// tile is **not** a live stepper (04) — its beats live at the bottom of
    /// Use (03 «Two fullscreens»), where a step cannot be pressed by accident
    /// while scrolling the lid.
    var tileRunsLive: Bool {
        switch self {
        case .counter, .tick, .reminder, .checklist, .timer: true
        case .stepper: false
        }
    }
}
