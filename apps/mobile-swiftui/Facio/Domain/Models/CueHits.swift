import Foundation

struct CueHits: Codable, Sendable, Equatable {
    var surfaced: Int
    var applied: Int

    init(surfaced: Int = 0, applied: Int = 0) {
        self.surfaced = surfaced
        self.applied = applied
    }
}
