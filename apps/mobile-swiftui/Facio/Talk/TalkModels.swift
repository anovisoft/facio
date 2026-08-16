import Foundation

enum ChatMessageKind: String, Codable, Sendable, Equatable {
    case user
    case assistant
    case snapshot
}

struct ChatSnapshot: Codable, Sendable, Equatable {
    var widgetId: String
    var subjectId: String
    var instanceId: String
    var version: Int
    var title: String
    var line: String

    enum CodingKeys: String, CodingKey {
        case widgetId = "widget_id"
        case subjectId = "subject_id"
        case instanceId = "instance_id"
        case version
        case title
        case line
    }
}

struct ChatMessage: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var kind: ChatMessageKind
    var text: String
    var snapshot: ChatSnapshot?
    var at: Date

    static func user(_ text: String, at: Date) -> ChatMessage {
        ChatMessage(id: UUID().uuidString, kind: .user, text: text, snapshot: nil, at: at)
    }

    static func assistant(_ text: String, at: Date) -> ChatMessage {
        ChatMessage(id: UUID().uuidString, kind: .assistant, text: text, snapshot: nil, at: at)
    }

    static func snapshot(_ card: ChatSnapshot, at: Date) -> ChatMessage {
        ChatMessage(id: UUID().uuidString, kind: .snapshot, text: card.line, snapshot: card, at: at)
    }
}

struct ChatThread: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var messages: [ChatMessage]
    var createdAt: Date
    var updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id
        case messages
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    static func empty(now: Date) -> ChatThread {
        ChatThread(id: UUID().uuidString, messages: [], createdAt: now, updatedAt: now)
    }
}

struct TalkArchive: Codable, Sendable, Equatable {
    var current: ChatThread
    var archived: [ChatThread]
}

struct TalkWireMessage: Codable, Sendable, Equatable {
    var role: String
    var text: String
}

struct TalkTurnRequest: Encodable, Sendable {
    var utterance: String
    var desk: DeskSnapshot
    var thread: [TalkWireMessage]
    var focusedWidgetId: String?
    var threadId: String?
    var now: Date?

    enum CodingKeys: String, CodingKey {
        case utterance
        case desk
        case thread
        case focusedWidgetId = "focused_widget_id"
        case threadId = "thread_id"
        case now
    }
}

struct TalkTurnResponse: Decodable, Sendable, Equatable {
    var text: String
    var desk: DeskSnapshot
    var mutated: Bool
    var snapshots: [ChatSnapshot]
    var threadId: String?

    enum CodingKeys: String, CodingKey {
        case text
        case desk
        case mutated
        case snapshots
        case threadId = "thread_id"
    }

    init(text: String, desk: DeskSnapshot, mutated: Bool, snapshots: [ChatSnapshot] = [], threadId: String? = nil) {
        self.text = text
        self.desk = desk
        self.mutated = mutated
        self.snapshots = snapshots
        self.threadId = threadId
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        text = try container.decode(String.self, forKey: .text)
        desk = try container.decode(DeskSnapshot.self, forKey: .desk)
        mutated = try container.decode(Bool.self, forKey: .mutated)
        snapshots = try container.decodeIfPresent([ChatSnapshot].self, forKey: .snapshots) ?? []
        threadId = try container.decodeIfPresent(String.self, forKey: .threadId)
    }
}
