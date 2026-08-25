import Foundation

struct AppleSignInRequest: Codable, Sendable {
    var identityToken: String

    enum CodingKeys: String, CodingKey {
        case identityToken = "identity_token"
    }
}

struct AppleSignInResponse: Codable, Sendable {
    var accountID: String
    var sessionToken: String

    enum CodingKeys: String, CodingKey {
        case accountID = "account_id"
        case sessionToken = "session_token"
    }
}
