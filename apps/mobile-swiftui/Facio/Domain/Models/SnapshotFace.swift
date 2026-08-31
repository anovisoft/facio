import Foundation

/// The state a chat snapshot was written with, as it arrives on the wire.
///
/// The service sends numbers; the sentence is drawn here, out of the client's
/// own catalog. Before this the card carried one finished Russian sentence and
/// nothing else, so an English lid showed «на паузе» under an English title —
/// and the very same phrase was already translated two files away
/// (`DisplayCopy.pausedNow`). Copy the person reads belongs to the client, and
/// it is not going to live in two places.
///
/// `nil` on a `ChatSnapshot` means an older service answered: then, and only
/// then, `line` is what gets drawn.
enum SnapshotFace: Codable, Sendable, Equatable {
    case counter(count: Int, goal: Int?)
    case tick(done: Bool)
    case checklist(done: Int, total: Int)
    case timer(seconds: Int)
    case stepper(step: Int, total: Int)
    /// `clock` is when it was set to fire, `closesAt` the door behind it.
    /// `skipped` is «not today» — the whole face, not a decoration on it.
    case reminder(clock: ClockTime?, closesAt: ClockTime?, skipped: Bool)
    /// The practice was frozen when the card was written.
    case paused
    /// Nothing to draw: a stepper with no beats, or a type with no face.
    case blank

    private enum CodingKeys: String, CodingKey {
        case kind
        case count
        case goal
        case done
        case total
        case seconds
        case step
        case clock
        case closesAt = "closes_at"
        case skipped
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        switch try container.decode(String.self, forKey: .kind) {
        case "counter":
            self = .counter(
                count: try container.decode(Int.self, forKey: .count),
                goal: try container.decodeIfPresent(Int.self, forKey: .goal)
            )
        case "tick":
            self = .tick(done: try container.decode(Bool.self, forKey: .done))
        case "checklist":
            self = .checklist(
                done: try container.decode(Int.self, forKey: .done),
                total: try container.decode(Int.self, forKey: .total)
            )
        case "timer":
            self = .timer(seconds: try container.decode(Int.self, forKey: .seconds))
        case "stepper":
            self = .stepper(
                step: try container.decode(Int.self, forKey: .step),
                total: try container.decode(Int.self, forKey: .total)
            )
        case "reminder":
            self = .reminder(
                clock: try container.decodeIfPresent(ClockTime.self, forKey: .clock),
                closesAt: try container.decodeIfPresent(ClockTime.self, forKey: .closesAt),
                skipped: try container.decodeIfPresent(Bool.self, forKey: .skipped) ?? false
            )
        case "paused":
            self = .paused
        default:
            // A kind this build has never heard of is not an error — the card
            // simply falls back to `line`, the way a pre-`face` client does.
            self = .blank
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .counter(let count, let goal):
            try container.encode("counter", forKey: .kind)
            try container.encode(count, forKey: .count)
            try container.encodeIfPresent(goal, forKey: .goal)
        case .tick(let done):
            try container.encode("tick", forKey: .kind)
            try container.encode(done, forKey: .done)
        case .checklist(let done, let total):
            try container.encode("checklist", forKey: .kind)
            try container.encode(done, forKey: .done)
            try container.encode(total, forKey: .total)
        case .timer(let seconds):
            try container.encode("timer", forKey: .kind)
            try container.encode(seconds, forKey: .seconds)
        case .stepper(let step, let total):
            try container.encode("stepper", forKey: .kind)
            try container.encode(step, forKey: .step)
            try container.encode(total, forKey: .total)
        case .reminder(let clock, let closesAt, let skipped):
            try container.encode("reminder", forKey: .kind)
            try container.encodeIfPresent(clock, forKey: .clock)
            try container.encodeIfPresent(closesAt, forKey: .closesAt)
            try container.encode(skipped, forKey: .skipped)
        case .paused:
            try container.encode("paused", forKey: .kind)
        case .blank:
            try container.encode("none", forKey: .kind)
        }
    }
}
