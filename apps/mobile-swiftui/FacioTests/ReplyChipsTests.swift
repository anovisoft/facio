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

/// The paths the kebab takes. It expands a talk **in place** and never goes
/// through `open`, so a row that only `open` cleared stood over a different
/// thread's composer — and a tap sent that sentence into it.
@MainActor
final class ReplyChipsPromoteTests: XCTestCase {
    private let stamp = FacioJSON.date(from: "2026-09-08T21:00:00")!

    func testExpandingAnotherTalkInTheKebabDoesNotCarryTheRowIntoIt() async throws {
        let (talk, _) = try makeTalk()
        talk.appendUser("старое")
        let other = talk.current.id
        talk.newChat()
        _ = await talk.send(utterance: "напомни в 19", desk: desk)
        XCTAssertEqual(talk.replyChips, ["Напомни завтра"])

        talk.promote(threadId: other)

        XCTAssertEqual(talk.replyChips, [])
    }

    /// Standing still on the same thread is still a new place to stand: the
    /// kebab promotes the current talk too, and the row belongs to the turn.
    func testPromotingTheCurrentTalkAlsoTakesTheRowDown() async throws {
        let (talk, _) = try makeTalk()
        _ = await talk.send(utterance: "напомни в 19", desk: desk)

        talk.promote(threadId: talk.current.id)

        XCTAssertEqual(talk.replyChips, [])
    }

    func testTakingTheTurnBackTakesItsOfferWithIt() async throws {
        let (talk, _) = try makeTalk()
        _ = await talk.send(utterance: "напомни в 19", desk: desk)
        let turn = try XCTUnwrap(talk.lastTurn)

        talk.markUndone(threadId: turn.threadId, turnId: turn.turnId)

        XCTAssertEqual(talk.replyChips, [], "the question no longer stands")
    }

    private var desk: DeskSnapshot {
        (try? SeedFactory.buildSeed(now: stamp)) ?? DeskSnapshot(subjects: [], cues: [], instances: [], widgets: [])
    }

    private func makeTalk() throws -> (TalkStore, TalkRepository) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-chips-promote-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = TalkRepository(directory: directory)
        let answer = TalkTurnResponse(
            text: "ок",
            desk: desk,
            mutated: false,
            replyChips: ["Напомни завтра"]
        )
        let store = try TalkStore(
            repository: repository,
            client: .stub { _ in answer },
            now: { self.stamp }
        )
        return (store, repository)
    }
}

/// The desk's clock runs at the wire's resolution (`FacioJSON.wireResolution`).
///
/// `string(from:)` writes whole seconds, so a `Date()` carrying fractional ones
/// is not equal to itself after a round trip — and the desk decides «did this
/// turn change anything» by exactly that comparison.
@MainActor
final class WireResolutionTests: XCTestCase {
    func testAStampSurvivesTheTripThroughTheService() throws {
        let ragged = Date(timeIntervalSince1970: 1_788_000_000.523)
        let stamped = FacioJSON.wireResolution(ragged)

        let encoded = FacioJSON.string(from: stamped)
        XCTAssertEqual(FacioJSON.date(from: encoded), stamped)
        XCTAssertNotEqual(FacioJSON.date(from: FacioJSON.string(from: ragged)), ragged)
    }

    /// The bug, end to end: a tick made by a finger, then a turn that only
    /// explained. The desk came back byte-identical, and before this it did
    /// not — so an undo was offered for a turn that changed nothing, and step 7
    /// counted it as mechanics.
    func testAnExplainOnlyTurnAfterATickIsNotAChange() throws {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-wire-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(SeedFactory.buildSeed(now: Date()))
        // The real clock on purpose: a fixed `now` in a test has whole seconds
        // and would never have shown this.
        let store = try DeskStore(repository: repository)
        store.toggleTick(widgetId: "vegetables-tick")

        let overTheWire = try roundTrip(store.snapshot)
        store.applyTalk(overTheWire, toolCalls: [], turn: TalkTurnRef(threadId: "t", turnId: "turn"))

        XCTAssertNil(store.undoableTurn, "nothing changed, so there is nothing to take back")
        let turns = DeskRepository(directory: directory).journal().filter { $0.type == .talkTurn }
        XCTAssertEqual(turns.last?.payload?["mutated"], "false")
    }

    private func roundTrip(_ snapshot: DeskSnapshot) throws -> DeskSnapshot {
        let data = try FacioJSON.encoder.encode(snapshot)
        return try FacioJSON.decoder.decode(DeskSnapshot.self, from: data)
    }
}
