import Foundation

enum CueSurface: String, Codable, Sendable, Equatable {
    case doTime = "do-time"
    case onDemand = "on-demand"
    case timing
    case placement
}
