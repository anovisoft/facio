import Foundation

enum ChatMessageKind: String, Codable, Sendable, Equatable {
    case user
    case assistant
    case snapshot
}

/// The centered card: a picture of a widget at the moment it was bound or
/// structurally changed. `face` and `detail` are what it was; `line` is the
/// finished sentence the service used to be the only author of. A card that
/// arrives without a `face` came from an older service and keeps its `line` —
/// see `SnapshotFaceLaw`.
struct ChatSnapshot: Codable, Sendable, Equatable {
    var widgetId: String
    var subjectId: String
    var instanceId: String
    var version: Int
    var title: String
    var line: String
    var face: SnapshotFace?
    /// The cue that rode under the number, in the words the person said it in.
    var detail: String?

    enum CodingKeys: String, CodingKey {
        case widgetId = "widget_id"
        case subjectId = "subject_id"
        case instanceId = "instance_id"
        case version
        case title
        case line
        case face
        case detail
    }
}

struct ChatMessage: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var kind: ChatMessageKind
    var text: String
    var snapshot: ChatSnapshot?
    var at: Date
    /// The turn this message belongs to: the person's line, the answer, and the
    /// snapshots under it share one. It is what the undo control hangs on, and
    /// what gets struck through together when the turn is taken back. Optional
    /// on purpose — a `talks.json` written before this exists still opens, and
    /// its turns simply carry no offer.
    var turnId: String?
    /// When the person took this turn back. Nothing is deleted (04): the
    /// bubbles and the snapshot stay exactly where they are and say so.
    var undoneAt: Date?

    static func user(_ text: String, at: Date, turnId: String? = nil) -> ChatMessage {
        ChatMessage(id: UUID().uuidString, kind: .user, text: text, snapshot: nil, at: at, turnId: turnId)
    }

    static func assistant(_ text: String, at: Date, turnId: String? = nil) -> ChatMessage {
        ChatMessage(id: UUID().uuidString, kind: .assistant, text: text, snapshot: nil, at: at, turnId: turnId)
    }

    static func snapshot(_ card: ChatSnapshot, at: Date, turnId: String? = nil) -> ChatMessage {
        ChatMessage(id: UUID().uuidString, kind: .snapshot, text: card.line, snapshot: card, at: at, turnId: turnId)
    }

    var isUndone: Bool { undoneAt != nil }
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

/// A phrase the person selected in the assistant's answer, on its way back to
/// the mouth. `quote` is the text itself — never an offset into a message, which
/// dangles the moment the method changes (04, Cue). The binding is only what the
/// client actually knows: the widget the sheet stands over and the subject
/// behind it. Nothing to bind means the turn owes text and nothing else — the
/// service refuses to guess a subject, and so does the client (05, «Ask about a
/// phrase, keep the answer»).
struct TalkSelection: Encodable, Sendable, Equatable {
    var quote: String
    var widgetId: String?
    var subjectId: String?
    var stepId: String?

    enum CodingKeys: String, CodingKey {
        case quote
        case widgetId = "widget_id"
        case subjectId = "subject_id"
        case stepId = "step_id"
    }
}

struct TalkTurnRequest: Encodable, Sendable {
    var utterance: String
    var desk: DeskSnapshot
    var thread: [TalkWireMessage]
    var focusedWidgetId: String?
    var selection: TalkSelection?
    var threadId: String?
    var now: Date?
    var locale: String = TalkLocale.current()

    enum CodingKeys: String, CodingKey {
        case utterance
        case desk
        case thread
        case focusedWidgetId = "focused_widget_id"
        case selection
        case threadId = "thread_id"
        case now
        case locale
    }
}

/// The mouth answers in the language the lid is showing, not in the one the
/// phone is set to. The bundle ships `ru` and `en`, so what iOS resolved for
/// the app is already one of the two the service accepts — anything else
/// would be a 422 on the wire.
enum TalkLocale {
    static func current(_ preferred: [String] = Bundle.main.preferredLocalizations) -> String {
        let head = preferred.first?.lowercased() ?? "ru"
        return head.hasPrefix("ru") ? "ru" : "en"
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
    /// The row over the composer (Q35). Plain sentences and nothing else: a
    /// chip carrying an id or an action would be a button that decides for the
    /// person, and tapping one here does exactly what typing it does.
    var replyChips: [String]

    enum CodingKeys: String, CodingKey {
        case text
        case desk
        case mutated
        case snapshots
        case toolCalls = "tool_calls"
        case threadId = "thread_id"
        case replyChips = "reply_chips"
    }

    init(
        text: String,
        desk: DeskSnapshot,
        mutated: Bool,
        snapshots: [ChatSnapshot] = [],
        toolCalls: [TalkToolCall] = [],
        threadId: String? = nil,
        replyChips: [String] = []
    ) {
        self.text = text
        self.desk = desk
        self.mutated = mutated
        self.snapshots = snapshots
        self.toolCalls = toolCalls
        self.threadId = threadId
        self.replyChips = replyChips
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        text = try container.decode(String.self, forKey: .text)
        desk = try container.decode(DeskSnapshot.self, forKey: .desk)
        mutated = try container.decode(Bool.self, forKey: .mutated)
        snapshots = try container.decodeIfPresent([ChatSnapshot].self, forKey: .snapshots) ?? []
        toolCalls = try container.decodeIfPresent([TalkToolCall].self, forKey: .toolCalls) ?? []
        threadId = try container.decodeIfPresent(String.self, forKey: .threadId)
        // Absent from a service written before Q35, and absent from most turns
        // even now: no row is the ordinary case, not a degraded one.
        replyChips = try container.decodeIfPresent([String].self, forKey: .replyChips) ?? []
    }
}
