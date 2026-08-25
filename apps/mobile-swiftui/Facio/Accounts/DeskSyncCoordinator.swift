import Foundation

/// Wires Sign in with Apple + `/v1/desk` sync to a `DeskStore`, without
/// touching the store's core commit path — the lid must keep ticking with
/// no session and no network. Nothing here is called automatically yet: no
/// UI exists to sign in from ("Настройки" is still the placeholder from
/// step 5), and this needs the Sign In with Apple capability enabled for
/// the app id on the Team ID in identity.md before it can be exercised on
/// device. Call `signIn`/`pushCurrentDesk` explicitly once that UI lands.
@MainActor
final class DeskSyncCoordinator {
    private let deskStore: DeskStore
    private let accountClient: AccountClient
    private let deskClient: DeskClient
    private let sessionStore: SessionStoring

    init(
        deskStore: DeskStore,
        accountClient: AccountClient = .live(),
        deskClient: DeskClient = .live(),
        sessionStore: SessionStoring = KeychainSessionStore()
    ) {
        self.deskStore = deskStore
        self.accountClient = accountClient
        self.deskClient = deskClient
        self.sessionStore = sessionStore
    }

    var currentSession: Session? { sessionStore.load() }

    /// Verify the Apple identity token, store the session, then pull
    /// whatever the server already has for this account and merge it in.
    @discardableResult
    func signIn(identityToken: String) async throws -> Session {
        let response = try await accountClient.signIn(identityToken: identityToken)
        let session = Session(accountID: response.accountID, sessionToken: response.sessionToken)
        sessionStore.save(session)
        if let serverDesk = try await deskClient.fetch(sessionToken: session.sessionToken) {
            deskStore.applyServerDesk(serverDesk)
        }
        return session
    }

    func signOut() {
        sessionStore.clear()
    }

    /// Push the local desk and apply back whatever the server resolved
    /// (structure LWW / progress merge — see apps/api desk/repository.py).
    /// No-op if not signed in; errors are the caller's to retry or ignore.
    func pushCurrentDesk() async throws {
        guard let session = sessionStore.load() else { return }
        let merged = try await deskClient.push(deskStore.snapshot, sessionToken: session.sessionToken)
        deskStore.applyServerDesk(merged)
    }
}
