import XCTest
@testable import Facio

@MainActor
final class TalkStoreTests: XCTestCase {
    func testNewChatArchivesCurrentAndStartsEmpty() throws {
        let talk = try makeTalk()
        talk.appendUser("поясница")
        let oldId = talk.current.id

        talk.newChat()

        XCTAssertTrue(talk.current.messages.isEmpty)
        XCTAssertNotEqual(talk.current.id, oldId)
        XCTAssertEqual(talk.archived.count, 1)
        XCTAssertEqual(talk.archived[0].id, oldId)
    }

    func testNewChatOnEmptyDoesNotArchive() throws {
        let talk = try makeTalk()
        let id = talk.current.id
        talk.newChat()
        XCTAssertEqual(talk.current.id, id)
        XCTAssertTrue(talk.archived.isEmpty)
    }

    func testCollapseDoesNotResetThread() throws {
        let talk = try makeTalk()
        talk.appendUser("hi")
        let id = talk.current.id
        talk.sheetOpen = true
        talk.sheetOpen = false
        XCTAssertEqual(talk.current.id, id)
        XCTAssertEqual(talk.current.messages.count, 1)
    }

    func testOpenArchivedSwapsCurrentAndOpensSheet() throws {
        let talk = try makeTalk()
        talk.appendUser("поясница")
        let first = talk.current.id
        talk.newChat()
        talk.appendUser("овощи")
        let second = talk.current.id

        talk.open(threadId: first)

        XCTAssertEqual(talk.current.id, first)
        XCTAssertTrue(talk.sheetOpen)
        XCTAssertEqual(talk.archived.first?.id, second)
        XCTAssertEqual(talk.listedThreads.count, 2)
    }

    func testOpenCurrentJustOpensSheet() throws {
        let talk = try makeTalk()
        talk.appendUser("hi")
        let id = talk.current.id
        talk.open(threadId: id)
        XCTAssertEqual(talk.current.id, id)
        XCTAssertTrue(talk.sheetOpen)
        XCTAssertTrue(talk.archived.isEmpty)
    }

    func testTalkTurnResponseDecodesSnakeCase() throws {
        let json = """
        {"text":"ok","desk":{"subjects":[],"cues":[],"instances":[],"widgets":[]},"mutated":true,"snapshots":[{"widget_id":"push-ups-counter","subject_id":"push-ups","instance_id":"push-ups-open","version":1,"title":"push-ups","line":"28 / 30"}],"thread_id":"t1"}
        """.data(using: .utf8)!
        let response = try FacioJSON.decoder.decode(TalkTurnResponse.self, from: json)
        XCTAssertEqual(response.text, "ok")
        XCTAssertTrue(response.mutated)
        XCTAssertEqual(response.snapshots[0].widgetId, "push-ups-counter")
        XCTAssertEqual(response.threadId, "t1")
    }

    func testSendAppendsAssistantAndSnapshot() async throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-talk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let desk = try SeedFactory.buildSeed(now: now)
        let cue = CueLaw.addCue(
            id: "push-ups-brace-talk",
            subjectId: "push-ups",
            kind: .correction,
            text: "держи корпус и ягодицы",
            surface: .doTime
        )
        let frozenDesk: DeskSnapshot = {
            var next = desk
            next.cues.append(cue)
            return next
        }()
        let snapshot = ChatSnapshot(
            widgetId: "push-ups-counter",
            subjectId: "push-ups",
            instanceId: "push-ups-open",
            version: 1,
            title: "push-ups",
            line: "28 / 30 · держи корпус и ягодицы"
        )
        let client = TalkClient.stub { request in
            TalkTurnResponse(
                text: "Держи корпус и ягодицы.",
                desk: frozenDesk,
                mutated: true,
                snapshots: [snapshot],
                threadId: request.threadId
            )
        }
        let talk = try TalkStore(repository: TalkRepository(directory: directory), client: client, now: { now })
        talk.draft = "поясница забирает нагрузку"

        let response = await talk.send(desk: desk)

        XCTAssertEqual(response?.mutated, true)
        XCTAssertEqual(talk.current.messages.count, 3)
        XCTAssertEqual(talk.current.messages[0].kind, .user)
        XCTAssertEqual(talk.current.messages[1].kind, .assistant)
        XCTAssertEqual(talk.current.messages[2].kind, .snapshot)
        XCTAssertEqual(talk.current.messages[2].snapshot?.widgetId, "push-ups-counter")
        XCTAssertEqual(talk.draft, "")
    }

    private func makeTalk() throws -> TalkStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-talk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return try TalkStore(
            repository: TalkRepository(directory: directory),
            client: .stub { _ in
                throw TalkClientError.transport
            }
        )
    }
}
