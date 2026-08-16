import Foundation

struct DeskSnapshot: Codable, Sendable, Equatable {
    var subjects: [Subject]
    var cues: [Cue]
    var instances: [Instance]
    var widgets: [Widget]
    var driftAsks: [String: DriftAskState]
    var driftAskedAt: [String: Date]

    enum CodingKeys: String, CodingKey {
        case subjects
        case cues
        case instances
        case widgets
        case driftAsks = "drift_asks"
        case driftAskedAt = "drift_asked_at"
    }

    init(
        subjects: [Subject],
        cues: [Cue],
        instances: [Instance],
        widgets: [Widget],
        driftAsks: [String: DriftAskState] = [:],
        driftAskedAt: [String: Date] = [:]
    ) {
        self.subjects = subjects
        self.cues = cues
        self.instances = instances
        self.widgets = widgets
        self.driftAsks = driftAsks
        self.driftAskedAt = driftAskedAt
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        subjects = try container.decode([Subject].self, forKey: .subjects)
        cues = try container.decode([Cue].self, forKey: .cues)
        instances = try container.decode([Instance].self, forKey: .instances)
        widgets = try container.decode([Widget].self, forKey: .widgets)
        driftAsks = try container.decodeIfPresent([String: DriftAskState].self, forKey: .driftAsks) ?? [:]
        driftAskedAt = try container.decodeIfPresent([String: Date].self, forKey: .driftAskedAt) ?? [:]
    }
}
