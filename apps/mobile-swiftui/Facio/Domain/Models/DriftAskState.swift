import Foundation

struct DriftAskState: Codable, Sendable, Equatable {
    var asksMade: Int
    var retireRefusals: Int

    enum CodingKeys: String, CodingKey {
        case asksMade = "asks_made"
        case retireRefusals = "retire_refusals"
    }

    init(asksMade: Int = 0, retireRefusals: Int = 0) {
        self.asksMade = asksMade
        self.retireRefusals = retireRefusals
    }
}
