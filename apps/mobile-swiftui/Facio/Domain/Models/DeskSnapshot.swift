import Foundation

struct DeskSnapshot: Codable, Sendable, Equatable {
    var subjects: [Subject]
    var cues: [Cue]
    var instances: [Instance]
    var widgets: [Widget]

    enum CodingKeys: String, CodingKey {
        case subjects
        case cues
        case instances
        case widgets
        // Retired keys, read only: the shrink ladder used to live in two side
        // tables on the desk and now rides each `Subject`. Kept in the decoder
        // so a `desk.json` written before R4 opens with its ladder intact.
        case legacyDriftAsks = "drift_asks"
        case legacyDriftAskedAt = "drift_asked_at"
    }

    private struct LegacyAskState: Decodable {
        var asksMade: Int
        var retireRefusals: Int

        enum CodingKeys: String, CodingKey {
            case asksMade = "asks_made"
            case retireRefusals = "retire_refusals"
        }
    }

    init(
        subjects: [Subject],
        cues: [Cue],
        instances: [Instance],
        widgets: [Widget]
    ) {
        self.subjects = subjects
        self.cues = cues
        self.instances = instances
        self.widgets = widgets
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        subjects = try container.decode([Subject].self, forKey: .subjects)
        cues = try container.decode([Cue].self, forKey: .cues)
        instances = try container.decode([Instance].self, forKey: .instances)
        widgets = try container.decode([Widget].self, forKey: .widgets)

        let asks = try container.decodeIfPresent([String: LegacyAskState].self, forKey: .legacyDriftAsks) ?? [:]
        let askedAt = try container.decodeIfPresent([String: Date].self, forKey: .legacyDriftAskedAt) ?? [:]
        guard !asks.isEmpty || !askedAt.isEmpty else { return }
        subjects = subjects.map { subject in
            var moved = subject
            if let state = asks[subject.id] {
                moved.driftAsksMade = max(moved.driftAsksMade, state.asksMade)
                moved.driftRetireRefusals = max(moved.driftRetireRefusals, state.retireRefusals)
            }
            if let stamp = askedAt[subject.id], moved.driftAskedAt == nil {
                moved.driftAskedAt = stamp
            }
            return moved
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(subjects, forKey: .subjects)
        try container.encode(cues, forKey: .cues)
        try container.encode(instances, forKey: .instances)
        try container.encode(widgets, forKey: .widgets)
    }
}
