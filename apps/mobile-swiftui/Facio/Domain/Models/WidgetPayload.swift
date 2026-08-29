import Foundation

/// What a runtime needs to run, ported 1:1 from `facio_domain.models`.
/// `count` / `target` are the counter, `done` the tick, `fireAt` the reminder,
/// `items` the checklist, `seconds` / `startedAt` / `elapsed` the timer,
/// `beats` / `current` the stepper. No stored progress number: how far a list has got is
/// counted by `ChecklistLaw` from the ticks themselves.
struct WidgetPayload: Codable, Sendable, Equatable {
    var count: Int?
    var target: Int?
    var done: Bool?
    var items: [ChecklistItem]?
    /// The length the person named, the moment the current run began
    /// («идёт с момента», empty while the timer stands still), and the seconds
    /// banked before it. Elapsed time is derived from those and the clock —
    /// there is no ticking number on the desk.
    var seconds: Int?
    var startedAt: Date?
    var elapsed: Int?
    /// The beats of a stepper and the one the person is standing on (0-based).
    var beats: [String]?
    var current: Int?
    var fireAt: Date?

    enum CodingKeys: String, CodingKey {
        case count
        case target
        case done
        case items
        case seconds
        case startedAt = "started_at"
        case elapsed
        case beats
        case current
        case fireAt = "fire_at"
    }

    init(
        count: Int? = nil,
        target: Int? = nil,
        done: Bool? = nil,
        items: [ChecklistItem]? = nil,
        seconds: Int? = nil,
        startedAt: Date? = nil,
        elapsed: Int? = nil,
        beats: [String]? = nil,
        current: Int? = nil,
        fireAt: Date? = nil
    ) {
        self.count = count
        self.target = target
        self.done = done
        self.items = items
        self.seconds = seconds
        self.startedAt = startedAt
        self.elapsed = elapsed
        self.beats = beats
        self.current = current
        self.fireAt = fireAt
    }
}
