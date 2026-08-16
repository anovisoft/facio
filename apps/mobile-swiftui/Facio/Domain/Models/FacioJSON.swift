import Foundation

enum FacioJSON {
    static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .custom(decodeDate)
        return decoder
    }()

    static let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.sortedKeys]
        encoder.dateEncodingStrategy = .custom(encodeDate)
        return encoder
    }()

    static func date(from string: String) -> Date? {
        let parts = string.split(separator: "T", maxSplits: 1, omittingEmptySubsequences: false)
        guard parts.count == 2 else { return nil }
        let day = parts[0].split(separator: "-")
        let clock = parts[1].split(separator: ":")
        guard day.count == 3, clock.count >= 2,
              let year = Int(day[0]),
              let month = Int(day[1]),
              let dayValue = Int(day[2]),
              let hour = Int(clock[0]),
              let minute = Int(clock[1])
        else { return nil }
        let second = clock.count > 2 ? Int(clock[2].prefix(2)) ?? 0 : 0
        var components = DateComponents()
        components.year = year
        components.month = month
        components.day = dayValue
        components.hour = hour
        components.minute = minute
        components.second = second
        return Calendar.current.date(from: components)
    }

    static func string(from date: Date) -> String {
        let parts = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute, .second], from: date)
        let year = parts.year ?? 0
        let month = parts.month ?? 0
        let day = parts.day ?? 0
        let hour = parts.hour ?? 0
        let minute = parts.minute ?? 0
        let second = parts.second ?? 0
        return String(format: "%04d-%02d-%02dT%02d:%02d:%02d", year, month, day, hour, minute, second)
    }

    private static func decodeDate(_ decoder: Decoder) throws -> Date {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        guard let date = date(from: raw) else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "bad Facio date \(raw)")
        }
        return date
    }

    private static func encodeDate(_ date: Date, _ encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(string(from: date))
    }
}
