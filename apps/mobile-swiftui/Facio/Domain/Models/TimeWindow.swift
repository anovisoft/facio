import Foundation

/// When the practice can still happen.
///
/// `hours` are the hours the person named, ordered and without repeats. One
/// window may hold several (Q34): «в 10, 12, 15, 16:30, 18, 21, 22» is one
/// practice firing seven times, not seven events with lives of their own.
/// Nothing here invents an hour nobody said.
///
/// `latestBy` is the first of them. It stays on the wire and on disk so a
/// `desk.json` and a service written before Q34 keep opening and keep being
/// read: one hour is a legal window and always was.
struct TimeWindow: Codable, Sendable, Equatable {
    private(set) var hours: [ClockTime]
    var closesAt: ClockTime?

    /// The first stated hour. Where a single `latest_by` used to live.
    var latestBy: ClockTime { hours.first ?? ClockTime(hour: 0, minute: 0) }

    enum CodingKeys: String, CodingKey {
        case hours
        case latestBy = "latest_by"
        case closesAt = "closes_at"
    }

    init(latestBy: ClockTime, closesAt: ClockTime? = nil) {
        self.init(hours: [latestBy], closesAt: closesAt)
    }

    init(hours: [ClockTime], closesAt: ClockTime? = nil) {
        self.hours = Self.ordered(hours)
        self.closesAt = closesAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        // A desk written before Q34 carries one `latest_by` and no `hours`.
        let stated = try container.decodeIfPresent([ClockTime].self, forKey: .hours) ?? []
        let single = try container.decodeIfPresent(ClockTime.self, forKey: .latestBy)
        var all = stated
        if let single, !all.contains(single) { all.append(single) }
        guard !all.isEmpty else {
            throw DecodingError.dataCorruptedError(
                forKey: .hours,
                in: container,
                debugDescription: "a window needs at least one stated hour"
            )
        }
        hours = Self.ordered(all)
        closesAt = try container.decodeIfPresent(ClockTime.self, forKey: .closesAt)
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(hours, forKey: .hours)
        // Written for a reader that only knows the old shape.
        try container.encode(latestBy, forKey: .latestBy)
        try container.encodeIfPresent(closesAt, forKey: .closesAt)
    }

    /// The nearest hour still ahead of `clock`, or the first one when the day
    /// is spent. What a face shows; the alarms still stand on all of them.
    func nextHour(after clock: ClockTime) -> ClockTime {
        hours.first { $0 >= clock } ?? latestBy
    }

    /// The hours behind the one a face is showing, in order. Empty when the
    /// window holds a single hour, which is the ordinary case.
    func hoursAfter(_ clock: ClockTime) -> [ClockTime] {
        hours.filter { $0 > clock }
    }

    /// Add an hour the person named. The same hour twice is the same hour, and
    /// an hour already standing is never quietly replaced.
    mutating func addHour(_ clock: ClockTime) {
        hours = Self.ordered(hours + [clock])
    }

    /// Drop an hour. Refuses to empty the window: a window with no hour cannot
    /// fire and cannot be drawn.
    @discardableResult
    mutating func removeHour(_ clock: ClockTime) -> Bool {
        let left = hours.filter { $0 != clock }
        guard !left.isEmpty, left.count != hours.count else { return false }
        hours = left
        return true
    }

    /// Move one hour to another — the picker on Use, where the person is
    /// editing the hour in front of them, not adding one.
    mutating func replaceHour(_ old: ClockTime, with clock: ClockTime) {
        hours = Self.ordered(hours.filter { $0 != old } + [clock])
    }

    private static func ordered(_ hours: [ClockTime]) -> [ClockTime] {
        Array(Set(hours)).sorted()
    }
}
