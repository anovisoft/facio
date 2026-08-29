import Foundation

struct Subject: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var title: String
    var cadence: Cadence
    var window: TimeWindow?
    var cueIds: [String]
    var target: Target?
    var instanceIds: [String]
    var status: SubjectStatus
    var pausedAt: Date?
    /// Q28 shrink ladder, remembered on the practice next to the pause. Three
    /// plain counters, not a score and not a streak (P7): how many times this
    /// subject was asked, how many times the offer to retire was refused, and
    /// when the last ask happened so the next one waits a full period.
    var driftAsksMade: Int
    var driftRetireRefusals: Int
    var driftAskedAt: Date?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case cadence
        case window
        case cueIds = "cue_ids"
        case target
        case instanceIds = "instance_ids"
        case status
        case pausedAt = "paused_at"
        case driftAsksMade = "drift_asks_made"
        case driftRetireRefusals = "drift_retire_refusals"
        case driftAskedAt = "drift_asked_at"
    }

    init(
        id: String,
        title: String,
        cadence: Cadence,
        window: TimeWindow? = nil,
        cueIds: [String] = [],
        target: Target? = nil,
        instanceIds: [String] = [],
        status: SubjectStatus = .active,
        pausedAt: Date? = nil,
        driftAsksMade: Int = 0,
        driftRetireRefusals: Int = 0,
        driftAskedAt: Date? = nil
    ) {
        self.id = id
        self.title = title
        self.cadence = cadence
        self.window = window
        self.cueIds = cueIds
        self.target = target
        self.instanceIds = instanceIds
        self.status = status
        self.pausedAt = pausedAt
        self.driftAsksMade = driftAsksMade
        self.driftRetireRefusals = driftRetireRefusals
        self.driftAskedAt = driftAskedAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        cadence = try container.decode(Cadence.self, forKey: .cadence)
        window = try container.decodeIfPresent(TimeWindow.self, forKey: .window)
        cueIds = try container.decodeIfPresent([String].self, forKey: .cueIds) ?? []
        target = try container.decodeIfPresent(Target.self, forKey: .target)
        instanceIds = try container.decodeIfPresent([String].self, forKey: .instanceIds) ?? []
        status = try container.decodeIfPresent(SubjectStatus.self, forKey: .status) ?? .active
        pausedAt = try container.decodeIfPresent(Date.self, forKey: .pausedAt)
        // A desk written before the ladder moved onto the subject still opens:
        // it simply starts on the first rung.
        driftAsksMade = try container.decodeIfPresent(Int.self, forKey: .driftAsksMade) ?? 0
        driftRetireRefusals = try container.decodeIfPresent(Int.self, forKey: .driftRetireRefusals) ?? 0
        driftAskedAt = try container.decodeIfPresent(Date.self, forKey: .driftAskedAt)
    }
}
