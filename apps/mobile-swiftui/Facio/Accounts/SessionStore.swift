import Foundation
import Security

/// The session token + account id from Sign in with Apple. Keychain, not
/// UserDefaults — this is a credential, not a preference.
struct Session: Equatable, Sendable {
    var accountID: String
    var sessionToken: String
}

protocol SessionStoring: Sendable {
    func load() -> Session?
    func save(_ session: Session)
    func clear()
}

struct KeychainSessionStore: SessionStoring {
    private let service = "com.anovisoft.facio.session"
    private let account = "current"

    func load() -> Session? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)
        guard status == errSecSuccess, let data = result as? Data else { return nil }
        return try? FacioJSON.decoder.decode(Session.self, from: data)
    }

    func save(_ session: Session) {
        guard let data = try? FacioJSON.encoder.encode(session) else { return }
        clear()
        var query = baseQuery()
        query[kSecValueData as String] = data
        query[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        SecItemAdd(query as CFDictionary, nil)
    }

    func clear() {
        SecItemDelete(baseQuery() as CFDictionary)
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}

extension Session: Codable {}
