import XCTest
@testable import Facio

@MainActor
final class DeskSyncCoordinatorTests: XCTestCase {
    func testSignInStoresSessionAndPullsServerDesk() async throws {
        let store = InMemorySessionStore()
        let desk = try makeDeskStore()
        let serverDesk: DeskSnapshot = {
            var next = desk.snapshot
            next.subjects = []
            return next
        }()

        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in
                AppleSignInResponse(accountID: "acct-1", sessionToken: "token-1")
            },
            deskClient: .stub(
                fetch: { _ in serverDesk },
                push: { snapshot, _ in snapshot }
            ),
            sessionStore: store
        )

        let session = try await coordinator.signIn(identityToken: "unused-in-stub")

        XCTAssertEqual(session.accountID, "acct-1")
        XCTAssertEqual(store.load()?.sessionToken, "token-1")
        XCTAssertTrue(desk.snapshot.subjects.isEmpty, "server desk should have been applied")
    }

    func testSignInWithNoServerDeskLeavesLocalUntouched() async throws {
        let store = InMemorySessionStore()
        let desk = try makeDeskStore()
        let before = desk.snapshot

        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in AppleSignInResponse(accountID: "acct-1", sessionToken: "token-1") },
            deskClient: .stub(fetch: { _ in nil }, push: { snapshot, _ in snapshot }),
            sessionStore: store
        )

        _ = try await coordinator.signIn(identityToken: "unused-in-stub")

        XCTAssertEqual(desk.snapshot, before)
    }

    func testPushCurrentDeskIsNoOpWithoutSession() async throws {
        let store = InMemorySessionStore()
        let desk = try makeDeskStore()
        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(fetch: { _ in nil }, push: { snapshot, _ in snapshot }),
            sessionStore: store
        )
        try await coordinator.pushCurrentDesk()
    }

    func testPushCurrentDeskAppliesServerMergeResult() async throws {
        let store = InMemorySessionStore()
        store.save(Session(accountID: "acct-1", sessionToken: "token-1"))
        let desk = try makeDeskStore()
        let merged: DeskSnapshot = {
            var next = desk.snapshot
            next.subjects = []
            return next
        }()

        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(fetch: { _ in nil }, push: { _, _ in merged }),
            sessionStore: store
        )

        try await coordinator.pushCurrentDesk()

        XCTAssertTrue(desk.snapshot.subjects.isEmpty)
    }

    func testSignOutClearsSession() throws {
        let store = InMemorySessionStore()
        store.save(Session(accountID: "a", sessionToken: "t"))
        let desk = try makeDeskStore()
        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(fetch: { _ in nil }, push: { snapshot, _ in snapshot }),
            sessionStore: store
        )
        coordinator.signOut()
        XCTAssertNil(store.load())
    }

    private func makeDeskStore() throws -> DeskStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-desk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return try DeskStore(repository: DeskRepository(directory: directory))
    }
}

/// In-memory `SessionStoring` for tests — the real Keychain store is
/// exercised separately in `SessionStoreTests`.
final class InMemorySessionStore: SessionStoring, @unchecked Sendable {
    private var stored: Session?
    func load() -> Session? { stored }
    func save(_ session: Session) { stored = session }
    func clear() { stored = nil }
}
