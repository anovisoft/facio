import Foundation

struct TimeWindow: Codable, Sendable, Equatable {
    var latestBy: ClockTime
    var closesAt: ClockTime?

    enum CodingKeys: String, CodingKey {
        case latestBy = "latest_by"
        case closesAt = "closes_at"
    }
}
