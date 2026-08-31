import Foundation
import Observation

/// Wires Sign in with Apple + `/v1/desk` sync to a `DeskStore`, without
/// touching the store's core commit path — the lid must keep ticking with
/// no session and no network (P5, plan В1–В2). Signing in is not a gate:
/// with no session every call here is silence, and the desk stays local.
///
/// Structure vs progress (Q20) is not re-implemented here: the merge lives
/// in `DeskStore.applyServerDesk`, which mirrors `applyTalk` and keeps a
/// local `.running` count from being eaten by a stale server write.
@Observable
@MainActor
final class DeskSyncCoordinator {
    private let deskStore: DeskStore
    private let accountClient: AccountClient
    private let deskClient: DeskClient
    private let sessionStore: SessionStoring
    private let now: () -> Date
    private var debounced: Task<Void, Never>?

    /// Mirror of the Keychain record, so views can observe it.
    private(set) var session: Session?
    /// A sign-in or a sync is in flight.
    private(set) var isBusy = false
    /// The last attempt did not reach the server. A calm line in Settings,
    /// never a modal — the lid does not care.
    private(set) var offline = false

    init(
        deskStore: DeskStore,
        accountClient: AccountClient = .live(),
        deskClient: DeskClient = .live(),
        sessionStore: SessionStoring = KeychainSessionStore(),
        now: @escaping () -> Date = Date.init
    ) {
        self.deskStore = deskStore
        self.accountClient = accountClient
        self.deskClient = deskClient
        self.sessionStore = sessionStore
        self.now = now
        self.session = sessionStore.load()
    }

    var currentSession: Session? { sessionStore.load() }

    var isSignedIn: Bool { session != nil }

    /// Verify the Apple identity token, store the session, then pull
    /// whatever the server already has for this account and merge it in.
    @discardableResult
    func signIn(identityToken: String, displayName: String? = nil) async throws -> Session {
        isBusy = true
        defer { isBusy = false }
        let response = try await accountClient.signIn(identityToken: identityToken)
        var next = Session(
            accountID: response.accountID,
            sessionToken: response.sessionToken,
            displayName: displayName
        )
        remember(next)
        do {
            if let serverDesk = try await deskClient.fetch(sessionToken: next.sessionToken) {
                deskStore.applyServerDesk(serverDesk)
            }
        } catch {
            offline = true
            throw error
        }
        next.lastSyncedAt = now()
        remember(next)
        offline = false
        return next
    }

    /// The session goes; the desk on this device stays exactly as it is.
    /// Signing out is not a punishment.
    func signOut() {
        debounced?.cancel()
        debounced = nil
        sessionStore.clear()
        session = nil
        offline = false
    }

    /// Push the local desk and apply back whatever the server resolved
    /// (structure LWW / progress merge — see apps/api desk/repository.py).
    /// No-op if not signed in; errors are the caller's to retry or ignore.
    func pushCurrentDesk() async throws {
        guard var current = sessionStore.load() else { return }
        let merged = try await deskClient.push(deskStore.snapshot, sessionToken: current.sessionToken)
        deskStore.applyServerDesk(merged)
        current.lastSyncedAt = now()
        remember(current)
    }

    /// The UI/foreground entry point: never throws, records `offline` instead.
    /// Silent without a session — nothing leaves the device before a login.
    func sync() async {
        guard sessionStore.load() != nil else { return }
        isBusy = true
        defer { isBusy = false }
        do {
            try await pushCurrentDesk()
            offline = false
        } catch {
            offline = true
        }
    }

    /// Local changes reach the server without a per-commit hook: the lid
    /// calls this on desk changes and the last call in a burst wins.
    func syncSoon(after seconds: Double = 2) {
        guard sessionStore.load() != nil else { return }
        debounced?.cancel()
        debounced = Task { [weak self] in
            if seconds > 0 {
                try? await Task.sleep(for: .seconds(seconds))
            }
            guard !Task.isCancelled else { return }
            await self?.sync()
        }
    }

    private func remember(_ next: Session) {
        sessionStore.save(next)
        session = next
    }
}
