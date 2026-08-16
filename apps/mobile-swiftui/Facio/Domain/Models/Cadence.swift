import Foundation

enum CadencePeriod: String, Codable, Sendable, Equatable {
    case day
    case week
    case none
}

enum CadenceError: Error, Equatable {
    case noneCannotCarryCount
    case countRequired
}

struct Cadence: Codable, Sendable, Equatable {
    var count: Int?
    var period: CadencePeriod

    var isNone: Bool { period == .none }

    init(count: Int?, period: CadencePeriod) throws {
        try Self.validate(count: count, period: period)
        self.count = count
        self.period = period
    }

    static func of(count: Int, period: CadencePeriod) throws -> Cadence {
        try Cadence(count: count, period: period)
    }

    static func none() throws -> Cadence {
        try Cadence(count: nil, period: .none)
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let count = try container.decodeIfPresent(Int.self, forKey: .count)
        let period = try container.decode(CadencePeriod.self, forKey: .period)
        try Self.validate(count: count, period: period)
        self.count = count
        self.period = period
    }

    private static func validate(count: Int?, period: CadencePeriod) throws {
        if period == .none {
            if count != nil { throw CadenceError.noneCannotCarryCount }
            return
        }
        guard let count, count >= 1 else { throw CadenceError.countRequired }
    }
}
