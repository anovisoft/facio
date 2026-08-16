import Foundation

enum WidgetStatus: String, Codable, Sendable, Equatable {
    case ready
    case running
    case done
    case skipped
    case snoozed
    case archived
}
