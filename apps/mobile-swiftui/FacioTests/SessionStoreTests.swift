import XCTest
@testable import Facio

final class SessionStoreTests: XCTestCase {
    func testSaveLoadClearRoundTrips() {
        let store = KeychainSessionStore()
        store.clear()
        XCTAssertNil(store.load())

        let session = Session(accountID: "acct-\(UUID().uuidString)", sessionToken: "token-abc")
        store.save(session)
        XCTAssertEqual(store.load(), session)

        store.clear()
        XCTAssertNil(store.load())
    }

    func testNameAndSyncStampRideWithTheSession() throws {
        let store = KeychainSessionStore()
        store.clear()
        let stamp = try XCTUnwrap(FacioJSON.date(from: "2026-08-29T10:00:00"))
        let session = Session(
            accountID: "acct-1",
            sessionToken: "token-1",
            displayName: "Ада",
            lastSyncedAt: stamp
        )
        store.save(session)
        XCTAssertEqual(store.load(), session)
        store.clear()
    }

    /// A record written before the name/stamp existed still opens.
    func testOlderRecordWithoutNameStillDecodes() throws {
        let legacy = Data(#"{"accountID":"a","sessionToken":"t"}"#.utf8)
        let session = try FacioJSON.decoder.decode(Session.self, from: legacy)
        XCTAssertEqual(session.accountID, "a")
        XCTAssertNil(session.displayName)
        XCTAssertNil(session.lastSyncedAt)
    }

    func testSaveOverwritesPreviousSession() {
        let store = KeychainSessionStore()
        store.save(Session(accountID: "a", sessionToken: "t1"))
        store.save(Session(accountID: "a", sessionToken: "t2"))
        XCTAssertEqual(store.load()?.sessionToken, "t2")
        store.clear()
    }
}
