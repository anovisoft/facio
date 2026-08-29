import Foundation

struct Widget: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var type: WidgetType
    var title: String
    var payload: WidgetPayload
    var status: WidgetStatus
    var when: Date?
    var section: WidgetSection
    var groupId: String?
    var subjectId: String
    var instanceId: String
    var tileSize: TileSize?
    var version: Int

    enum CodingKeys: String, CodingKey {
        case id
        case type
        case title
        case payload
        case status
        case when
        case section
        case groupId = "group_id"
        case subjectId = "subject_id"
        case instanceId = "instance_id"
        case tileSize = "tile_size"
        case version
    }

    init(
        id: String,
        type: WidgetType,
        title: String,
        payload: WidgetPayload = WidgetPayload(),
        status: WidgetStatus,
        when: Date? = nil,
        section: WidgetSection,
        groupId: String? = nil,
        subjectId: String,
        instanceId: String,
        tileSize: TileSize? = nil,
        version: Int = 1
    ) {
        self.id = id
        self.type = type
        self.title = title
        self.payload = payload
        self.status = status
        self.when = when
        self.section = section
        self.groupId = groupId
        self.subjectId = subjectId
        self.instanceId = instanceId
        self.tileSize = tileSize
        self.version = version
    }

    var counterCount: Int { payload.count ?? 0 }
    var counterTarget: Int { payload.target ?? 0 }
    /// The goal the person actually named. Missing or `0` is not a goal — the
    /// law does not draw «0 / 0» (`_snapshot_line`) and neither does the lid.
    var counterGoal: Int? {
        guard let target = payload.target, target > 0 else { return nil }
        return target
    }
    var isTickDone: Bool { payload.done == true || status == .done }
    var reminderFireAt: Date? { payload.fireAt ?? when }
}
