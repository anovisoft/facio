import Foundation

struct WidgetPayload: Codable, Sendable, Equatable {
    var count: Int?
    var target: Int?
    var done: Bool?
    var fireAt: Date?

    enum CodingKeys: String, CodingKey {
        case count
        case target
        case done
        case fireAt = "fire_at"
    }

    init(count: Int? = nil, target: Int? = nil, done: Bool? = nil, fireAt: Date? = nil) {
        self.count = count
        self.target = target
        self.done = done
        self.fireAt = fireAt
    }
}
