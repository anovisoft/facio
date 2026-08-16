import Foundation

struct ClockTime: Codable, Sendable, Equatable, Hashable, Comparable {
    var hour: Int
    var minute: Int
    var second: Int

    init(hour: Int, minute: Int, second: Int = 0) {
        self.hour = hour
        self.minute = minute
        self.second = second
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        let parts = raw.split(separator: ":")
        guard parts.count >= 2,
              let hour = Int(parts[0]),
              let minute = Int(parts[1])
        else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "bad clock \(raw)")
        }
        self.hour = hour
        self.minute = minute
        self.second = parts.count > 2 ? Int(parts[2]) ?? 0 : 0
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(String(format: "%02d:%02d:%02d", hour, minute, second))
    }

    var shortLabel: String {
        String(format: "%d:%02d", hour, minute)
    }

    static func < (lhs: ClockTime, rhs: ClockTime) -> Bool {
        (lhs.hour, lhs.minute, lhs.second) < (rhs.hour, rhs.minute, rhs.second)
    }
}
