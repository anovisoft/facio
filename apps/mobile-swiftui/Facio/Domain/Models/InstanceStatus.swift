import Foundation

enum InstanceStatus: String, Codable, Sendable, Equatable {
    case completed
    case prepared
    case inProgress = "in_progress"
}
