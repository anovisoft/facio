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

enum TalkJSONValue: Decodable, Sendable, Equatable {
    case string(String)
    case int(Int)
    case double(Double)
    case bool(Bool)
    case object([String: TalkJSONValue])
    case array([TalkJSONValue])
    case null

    var string: String? {
        switch self {
        case .string(let value): value
        default: nil
        }
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(Int.self) {
            self = .int(value)
        } else if let value = try? container.decode(Double.self) {
            self = .double(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode([String: TalkJSONValue].self) {
            self = .object(value)
        } else if let value = try? container.decode([TalkJSONValue].self) {
            self = .array(value)
        } else {
            throw DecodingError.dataCorruptedError(in: container, debugDescription: "unsupported JSON value")
        }
    }
}

struct TalkToolCall: Decodable, Sendable, Equatable {
    var name: String
    var arguments: [String: TalkJSONValue] = [:]
    var ok: Bool
    var error: String? = nil
}

struct TalkTurnResponse: Decodable, Sendable, Equatable {
    var text: String
    var desk: DeskSnapshot
    var mutated: Bool
    var snapshots: [ChatSnapshot]
    var toolCalls: [TalkToolCall]
    var threadId: String?

    enum CodingKeys: String, CodingKey {
        case text
        case desk
        case mutated
        case snapshots
        case toolCalls = "tool_calls"
        case threadId = "thread_id"
    }

    init(
        text: String,
        desk: DeskSnapshot,
        mutated: Bool,
        snapshots: [ChatSnapshot] = [],
        toolCalls: [TalkToolCall] = [],
        threadId: String? = nil
    ) {
        self.text = text
        self.desk = desk
        self.mutated = mutated
        self.snapshots = snapshots
        self.toolCalls = toolCalls
        self.threadId = threadId
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        text = try container.decode(String.self, forKey: .text)
        desk = try container.decode(DeskSnapshot.self, forKey: .desk)
        mutated = try container.decode(Bool.self, forKey: .mutated)
        snapshots = try container.decodeIfPresent([ChatSnapshot].self, forKey: .snapshots) ?? []
        toolCalls = try container.decodeIfPresent([TalkToolCall].self, forKey: .toolCalls) ?? []
        threadId = try container.decodeIfPresent(String.self, forKey: .threadId)
    }
}
