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

    func testSaveOverwritesPreviousSession() {
        let store = KeychainSessionStore()
        store.save(Session(accountID: "a", sessionToken: "t1"))
        store.save(Session(accountID: "a", sessionToken: "t2"))
        XCTAssertEqual(store.load()?.sessionToken, "t2")
        store.clear()
    }
}
