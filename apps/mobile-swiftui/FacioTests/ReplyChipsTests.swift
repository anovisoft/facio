import XCTest
@testable import Facio

/// Q35 on the client. A chip is the sentence the person is about to say, and
/// the only thing that makes it a chip rather than a button is that it lives
/// for exactly one turn and does exactly what typing would do.
@MainActor
final class ReplyChipsTests: XCTestCase {
    private let stamp = FacioJSON.date(from: "2026-09-08T21:00:00")!

    func testAnOlderServiceThatSendsNoRowIsNotADegradedCase() throws {
        // No `reply_chips` on the wire at all — every turn written before Q35,
        // and most turns after it.
        let json = Data("""
        {"text":"ок","desk":\(deskJSON),"mutated":false}
        """.utf8)
        let decoded = try FacioJSON.decoder.decode(TalkTurnResponse.self, from: json)
        XCTAssertEqual(decoded.replyChips, [])
    }

    func testTheRowComesOffTheWireInTheAnswersLanguage() async throws {
        let (talk, _) = try makeTalk(answering: response(chips: ["Напомни завтра"]))
        _ = await talk.send(utterance: "напомни в 19", desk: desk)

        XCTAssertEqual(talk.replyChips, ["Напомни завтра"])
    }

    /// The rule the whole feature hangs on: the row belongs to the question it
    /// answered. A chip still standing over the field two turns later would be
    /// a control panel, and tapping it would answer something already settled.
    func testTheRowDiesWithItsTurn() async throws {
        let (talk, box) = try makeTalk(answering: response(chips: ["Напомни завтра"]))
        _ = await talk.send(utterance: "напомни в 19", desk: desk)
        XCTAssertFalse(talk.replyChips.isEmpty)

        box.answer = response(chips: [])
        _ = await talk.send(utterance: "спасибо", desk: desk)
        XCTAssertEqual(talk.replyChips, [])
    }

    /// Cleared **before** the turn goes out, not when the answer comes back.
    /// The distinguishing case is a turn that never arrives: clearing on
    /// success would leave yesterday's offer standing over a failed send, and
    /// the person would tap an answer to a question nothing is listening to.
    func testAFailedTurnStillTakesTheOfferDown() async throws {
        let (talk, box) = try makeTalk(answering: response(chips: ["Напомни завтра"]))
        _ = await talk.send(utterance: "напомни в 19", desk: desk)
        XCTAssertFalse(talk.replyChips.isEmpty)

        box.failing = true
        _ = await talk.send(utterance: "а если завтра", desk: desk)

        XCTAssertEqual(talk.replyChips, [])
        XCTAssertNotNil(talk.errorMessage, "the send really did fail")
    }

    func testANewChatDoesNotInheritTheOfferOfTheOldOne() async throws {
        let (talk, _) = try makeTalk(answering: response(chips: ["Напомни завтра"]))
        _ = await talk.send(utterance: "напомни в 19", desk: desk)

        talk.newChat()
        XCTAssertEqual(talk.replyChips, [])
    }

    func testOpeningAnOldTalkDoesNotHandBackAnOffer() async throws {
        let (talk, _) = try makeTalk(answering: response(chips: ["Напомни завтра"]))
        talk.appendUser("старое")
        let old = talk.current.id
        talk.newChat()
        _ = await talk.send(utterance: "напомни в 19", desk: desk)
        XCTAssertFalse(talk.replyChips.isEmpty)

        talk.open(threadId: old)
        XCTAssertEqual(talk.replyChips, [])
    }

    /// A day-0 chip fills the field without sending; a reply chip sends. They
    /// are two different things and must not leave each other's row standing.
    func testADayZeroChipClearsTheReplyRow() async throws {
        let (talk, _) = try makeTalk(answering: response(chips: ["Напомни завтра"]))
        _ = await talk.send(utterance: "напомни в 19", desk: desk)

        talk.startDraft("пробежка")
        XCTAssertEqual(talk.replyChips, [])
        XCTAssertEqual(talk.draft, "пробежка")
    }

    // MARK: - Helpers

    private var desk: DeskSnapshot {
        (try? SeedFactory.buildSeed(now: stamp)) ?? DeskSnapshot(subjects: [], cues: [], instances: [], widgets: [])
    }

    private var deskJSON: String {
        let data = (try? FacioJSON.encoder.encode(desk)) ?? Data("{}".utf8)
        return String(data: data, encoding: .utf8) ?? "{}"
    }

    private func response(chips: [String]) -> TalkTurnResponse {
        TalkTurnResponse(text: "ок", desk: desk, mutated: false, replyChips: chips)
    }

    private func makeTalk(answering answer: TalkTurnResponse) throws -> (TalkStore, AnswerBox) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-chips-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let box = AnswerBox(answer: answer)
        let store = try TalkStore(
            repository: TalkRepository(directory: directory),
            client: .stub { [box] _ in
                if box.failing { throw TalkClientError.transport }
                return box.answer
            },
            now: { self.stamp }
        )
        return (store, box)
    }
}

/// What the stubbed client answers next. Locked because the client hands the
/// closure across an actor boundary — the same reason `TalkUndoTests` locks the
/// thread it records.
private final class AnswerBox: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: TalkTurnResponse
    private var down = false

    init(answer: TalkTurnResponse) {
        stored = answer
    }

    var answer: TalkTurnResponse {
        get { lock.withLock { stored } }
        set { lock.withLock { stored = newValue } }
    }

    /// The pipe is gone. The lid goes on working; the offer must not.
    var failing: Bool {
        get { lock.withLock { down } }
        set { lock.withLock { down = newValue } }
    }
}
