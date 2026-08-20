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
        pausedAt: Date? = nil
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
    }
}
