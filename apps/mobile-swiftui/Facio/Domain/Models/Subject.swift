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

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case cadence
        case window
        case cueIds = "cue_ids"
        case target
        case instanceIds = "instance_ids"
        case status
    }

    init(
        id: String,
        title: String,
        cadence: Cadence,
        window: TimeWindow? = nil,
        cueIds: [String] = [],
        target: Target? = nil,
        instanceIds: [String] = [],
        status: SubjectStatus = .active
    ) {
        self.id = id
        self.title = title
        self.cadence = cadence
        self.window = window
        self.cueIds = cueIds
        self.target = target
        self.instanceIds = instanceIds
        self.status = status
    }
}
