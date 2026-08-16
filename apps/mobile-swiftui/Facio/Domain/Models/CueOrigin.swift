import Foundation

struct CueOrigin: Codable, Sendable, Equatable {
    var chatId: String?
    var messageId: String?

    enum CodingKeys: String, CodingKey {
        case chatId = "chat_id"
        case messageId = "message_id"
    }
}
