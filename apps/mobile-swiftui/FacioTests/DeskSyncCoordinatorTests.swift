import XCTest
@testable import Facio

@MainActor
final class DeskSyncCoordinatorTests: XCTestCase {
    func testSignInStoresSessionAndPullsServerDesk() async throws {
        let store = InMemorySessionStore()
        let desk = try makeDeskStore()
        XCTAssertFalse(desk.snapshot.subjects.isEmpty)
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
            sessionStore: store,
            now: { Self.stamp }
        )

        let session = try await coordinator.signIn(identityToken: "unused-in-stub", displayName: "Ада")

        XCTAssertEqual(session.accountID, "acct-1")
        XCTAssertEqual(store.load()?.sessionToken, "token-1")
        XCTAssertEqual(store.load()?.displayName, "Ада")
        XCTAssertEqual(store.load()?.lastSyncedAt, Self.stamp)
        XCTAssertEqual(coordinator.session?.accountID, "acct-1")
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
        let pushed = Box()
        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(
                fetch: { _ in nil },
                push: { snapshot, _ in
                    pushed.hit = true
                    return snapshot
                }
            ),
            sessionStore: store
        )

        try await coordinator.pushCurrentDesk()
        await coordinator.sync()
        coordinator.syncSoon(after: 0)

        XCTAssertFalse(pushed.hit, "nothing may leave the device without a session")
        XCTAssertFalse(coordinator.isSignedIn)
        XCTAssertFalse(coordinator.offline)
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
            sessionStore: store,
            now: { Self.stamp }
        )

        try await coordinator.pushCurrentDesk()

        XCTAssertTrue(desk.snapshot.subjects.isEmpty)
        XCTAssertEqual(store.load()?.lastSyncedAt, Self.stamp)
    }

    /// Q20: structure is last-write-wins, runtime progress is not. A stale
    /// server answer must not eat a set counted on this device.
    func testSyncDoesNotRollBackRunningProgress() async throws {
        let session = InMemorySessionStore()
        session.save(Session(accountID: "acct-1", sessionToken: "token-1"))
        let desk = try makeDeskStore()
        desk.tickCounter(widgetId: "push-ups-counter", delta: 1)
        let local = try XCTUnwrap(desk.widget(id: "push-ups-counter"))
        XCTAssertEqual(local.status, .running)

        let stale: DeskSnapshot = {
            var next = desk.snapshot
            guard let index = next.widgets.firstIndex(where: { $0.id == "push-ups-counter" }) else { return next }
            next.widgets[index].payload.count = 4
            next.widgets[index].status = .ready
            return next
        }()

        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(fetch: { _ in nil }, push: { _, _ in stale }),
            sessionStore: session
        )

        try await coordinator.pushCurrentDesk()

        XCTAssertEqual(desk.widget(id: "push-ups-counter")?.counterCount, local.counterCount)
        XCTAssertEqual(desk.widget(id: "push-ups-counter")?.status, .running)
    }

    func testSignOutClearsSessionAndKeepsTheDesk() throws {
        let store = InMemorySessionStore()
        store.save(Session(accountID: "a", sessionToken: "t"))
        let desk = try makeDeskStore()
        let before = desk.snapshot
        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(fetch: { _ in nil }, push: { snapshot, _ in snapshot }),
            sessionStore: store
        )

        coordinator.signOut()

        XCTAssertNil(store.load())
        XCTAssertNil(coordinator.session)
        XCTAssertEqual(desk.snapshot, before, "signing out is not a punishment for the desk")
    }

    /// No network: the sync says so, the session survives, the desk is intact.
    func testSyncWithoutNetworkGoesOfflineAndKeepsEverything() async throws {
        let store = InMemorySessionStore()
        store.save(Session(accountID: "acct-1", sessionToken: "token-1"))
        let desk = try makeDeskStore()
        let before = desk.snapshot
        let coordinator = DeskSyncCoordinator(
            deskStore: desk,
            accountClient: .stub { _ in throw TalkClientError.transport },
            deskClient: .stub(fetch: { _ in nil }, push: { _, _ in throw TalkClientError.transport }),
            sessionStore: store
        )

        await coordinator.sync()

        XCTAssertTrue(coordinator.offline)
        XCTAssertTrue(coordinator.isSignedIn)
        XCTAssertEqual(desk.snapshot, before)
    }

    private static let stamp = FacioJSON.date(from: "2026-08-29T10:00:00")!

    private func makeDeskStore(now: Date = Date()) throws -> DeskStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-desk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        // A device that already has a desk — the interesting case for sync.
        try repository.saveSnapshot(SeedFactory.buildSeed(now: now))
        return try DeskStore(repository: repository, now: { now })
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

/// Mutable flag reachable from a `@Sendable` stub closure.
private final class Box: @unchecked Sendable {
    var hit = false
}
