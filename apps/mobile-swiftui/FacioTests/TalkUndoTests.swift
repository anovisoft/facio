import XCTest
@testable import Facio

/// The one step back (P6 «visible mutation, reversible»; 06 AI #2 «no visible
/// change, no undo»). The desk goes back to what it was before the last talk
/// turn that changed it — and what fingers did in the meantime stays.
@MainActor
final class TalkUndoTests: XCTestCase {
    private let stamp = FacioJSON.date(from: "2026-08-16T12:00:00")!

    // MARK: - The desk

    func testUndoTakesTheDeskBackToBeforeTheTurn() throws {
        let (store, _, _) = try makeDesk()
        XCTAssertNil(store.undoableTurn)

        try writeGym(into: store)

        XCTAssertNotNil(store.widget(id: "gym-counter"))
        XCTAssertNotNil(store.subject(id: "gym"))
        XCTAssertTrue(store.undoOffered(threadId: "t1", turnId: "turn-1"))

        store.undoLastTalk()

        XCTAssertNil(store.widget(id: "gym-counter"))
        XCTAssertNil(store.subject(id: "gym"))
        XCTAssertFalse(store.snapshot.instances.contains { $0.id == "gym-open" })
        XCTAssertNil(store.undoableTurn)
    }

    /// Q20 and 06 AI #2 in one line: the rollback restores **structure**, and a
    /// set counted on this device in between is not structure.
    func testUndoKeepsProgressMadeAfterTheTurn() throws {
        let (store, _, _) = try makeDesk()
        try writeGym(into: store)

        // A counter turned after the turn, and a tick closed after the turn —
        // one running, one done, both on widgets the turn never named.
        store.tickCounter(widgetId: "push-ups-counter", delta: 3)
        store.toggleTick(widgetId: "vegetables-tick")
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 31)
        XCTAssertEqual(store.widget(id: "vegetables-tick")?.status, .done)

        store.undoLastTalk()

        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 31)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .running)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "push-ups-open" }?.status, .inProgress)
        XCTAssertEqual(store.widget(id: "vegetables-tick")?.status, .done)
        XCTAssertEqual(store.widget(id: "vegetables-tick")?.payload.done, true)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "vegetables-open" }?.status, .completed)
        // …and the structure the turn wrote is gone all the same.
        XCTAssertNil(store.widget(id: "gym-counter"))
    }

    /// One rung, not a ladder: a newer turn that changed the desk takes the
    /// offer away from the older one.
    func testNewerChangingTurnTakesTheOffer() throws {
        let (store, _, _) = try makeDesk()
        try writeGym(into: store)

        var second = store.snapshot
        second.widgets.removeAll { $0.id == "vegetables-tick" }
        store.applyTalk(second, turn: TalkTurnRef(threadId: "t1", turnId: "turn-2"))

        XCTAssertFalse(store.undoOffered(threadId: "t1", turnId: "turn-1"))
        XCTAssertTrue(store.undoOffered(threadId: "t1", turnId: "turn-2"))

        store.undoLastTalk()

        // The second turn came back; the first one stays done — one step.
        XCTAssertNotNil(store.widget(id: "vegetables-tick"))
        XCTAssertNotNil(store.widget(id: "gym-counter"))
    }

    /// «What is brisket?» leaves no mark on the desk, so it does not take the
    /// offer off the change standing above it (P3: explaining is a legal
    /// outcome, and never-do AI #8 forbids forcing a patch after one).
    func testExplainOnlyTurnLeavesTheOfferWhereItWas() throws {
        let (store, _, _) = try makeDesk()
        try writeGym(into: store)

        store.applyTalk(store.snapshot, turn: TalkTurnRef(threadId: "t1", turnId: "turn-2"))

        XCTAssertTrue(store.undoOffered(threadId: "t1", turnId: "turn-1"))
    }

    /// Disk, not memory: the offer is visible in a thread that survives a
    /// relaunch, and a button that stopped working while it was still on screen
    /// is «no undo» with extra steps.
    func testOfferSurvivesRelaunch() throws {
        let (store, repository, _) = try makeDesk()
        try writeGym(into: store)

        let relaunched = try DeskStore(repository: repository, now: { self.stamp })
        XCTAssertTrue(relaunched.undoOffered(threadId: "t1", turnId: "turn-1"))

        relaunched.undoLastTalk()
        XCTAssertNil(relaunched.widget(id: "gym-counter"))

        let again = try DeskStore(repository: repository, now: { self.stamp })
        XCTAssertNil(again.undoableTurn)
        XCTAssertNil(again.widget(id: "gym-counter"))
    }

    func testUndoIsSpentOnce() throws {
        let (store, _, _) = try makeDesk()
        try writeGym(into: store)

        XCTAssertNotNil(store.undoLastTalk())
        XCTAssertNil(store.undoLastTalk())
        // Nothing came back: undoing an undo is a time machine, which this is not.
        XCTAssertNil(store.widget(id: "gym-counter"))
    }

    /// The practice the turn created, removed by hand before the undo. The desk
    /// the turn started from never had it, so there is nothing to resurrect and
    /// the two land in the same place — the manual removal is simply absorbed.
    func testManualRemovalBeforeUndoLeavesNothingToResurrect() throws {
        let (store, _, _) = try makeDesk()
        try writeGym(into: store)

        XCTAssertTrue(store.removeFromLid(subjectId: "gym"))
        XCTAssertEqual(store.subject(id: "gym")?.status, .retired)

        store.undoLastTalk()

        XCTAssertNil(store.subject(id: "gym"))
        XCTAssertNil(store.widget(id: "gym-counter"))
    }

    func testUndoWritesTheJournalEvent() throws {
        let (store, _, directory) = try makeDesk()
        try writeGym(into: store)
        store.undoLastTalk()

        let events = try journal(in: directory)
        let undone = try XCTUnwrap(events.last { $0.type == .talkUndone })
        XCTAssertEqual(undone.payload?["thread"], "t1")
        XCTAssertEqual(undone.payload?["turn"], "turn-1")
    }

    /// A desk from the server is the record of truth speaking; a desk from
    /// before a turn is not a thing to push over it.
    func testServerDeskTakesTheOfferAway() throws {
        let (store, _, _) = try makeDesk()
        try writeGym(into: store)

        store.applyServerDesk(store.snapshot)

        XCTAssertNil(store.undoableTurn)
    }

    // MARK: - The thread

    /// Nothing is deleted as punishment (04): the line, the answer and the
    /// snapshot stay where they are, marked.
    func testUndoMarksTheWholeTurnAndKeepsIt() async throws {
        let (desk, _, _) = try makeDesk()
        let talk = try makeTalk(answering: try gymDesk(from: desk.snapshot))
        talk.draft = "запиши зал"

        let response = await talk.send(desk: desk.snapshot)
        XCTAssertEqual(response?.mutated, true)
        desk.applyTalk(response!.desk, toolCalls: response!.toolCalls, turn: talk.lastTurn)
        XCTAssertEqual(talk.current.messages.count, 3)
        XCTAssertNotNil(desk.undoableTurn)

        TalkActions.undo(talk: talk, desk: desk)

        XCTAssertEqual(talk.current.messages.count, 3)
        XCTAssertTrue(talk.current.messages.allSatisfy(\.isUndone))
        XCTAssertEqual(talk.current.messages[2].snapshot?.widgetId, "gym-counter")
        XCTAssertNil(desk.widget(id: "gym-counter"))
        XCTAssertNil(desk.undoableTurn)
    }

    /// An undone turn does not travel back to the mouth: the desk on the same
    /// wire no longer carries what it wrote, and a history still saying
    /// «записал зал» is an invitation to write it again (06 AI #2).
    func testUndoneTurnStaysOutOfTheWireHistory() async throws {
        let (desk, _, _) = try makeDesk()
        let seen = LockedThread()
        let answer = try gymDesk(from: desk.snapshot)
        let talk = try makeTalk(answering: answer, seen: seen)

        talk.draft = "запиши зал"
        _ = await talk.send(desk: desk.snapshot)
        desk.applyTalk(answer, turn: talk.lastTurn)
        TalkActions.undo(talk: talk, desk: desk)

        talk.draft = "что такое брискет"
        _ = await talk.send(desk: desk.snapshot)

        // The history handed to the mouth on the second turn is what was said
        // before it, minus the turn the person took back — here, nothing.
        XCTAssertTrue(seen.value.isEmpty, "the undone turn still travelled: \(seen.value.map(\.text))")
    }

    // MARK: - Helpers

    private func makeDesk() throws -> (DeskStore, DeskRepository, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-undo-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(SeedFactory.buildSeed(now: stamp))
        return (try DeskStore(repository: repository, now: { self.stamp }), repository, directory)
    }

    private func makeTalk(answering desk: DeskSnapshot, seen: LockedThread? = nil) throws -> TalkStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-undo-talk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let card = ChatSnapshot(
            widgetId: "gym-counter",
            subjectId: "gym",
            instanceId: "gym-open",
            version: 1,
            title: "зал",
            line: "зал"
        )
        let client = TalkClient.stub { request in
            seen?.value = request.thread
            return TalkTurnResponse(
                text: "Записал зал.",
                desk: desk,
                mutated: true,
                snapshots: [card],
                threadId: request.threadId
            )
        }
        return try TalkStore(
            repository: TalkRepository(directory: directory),
            client: client,
            now: { self.stamp }
        )
    }

    /// The desk a turn that wrote «зал» hands back.
    private func gymDesk(from base: DeskSnapshot) throws -> DeskSnapshot {
        var incoming = base
        incoming.subjects.append(
            Subject(
                id: "gym",
                title: "зал",
                cadence: try Cadence.of(count: 3, period: .week),
                instanceIds: ["gym-open"]
            )
        )
        incoming.instances.append(Instance(id: "gym-open", subjectId: "gym", when: stamp, status: .prepared))
        incoming.widgets.append(
            Widget(
                id: "gym-counter",
                type: .counter,
                title: "зал",
                payload: WidgetPayload(count: 0, target: 0),
                status: .ready,
                section: .today,
                subjectId: "gym",
                instanceId: "gym-open",
                tileSize: .compact
            )
        )
        return incoming
    }

    private func writeGym(into store: DeskStore) throws {
        store.applyTalk(
            try gymDesk(from: store.snapshot),
            toolCalls: [
                TalkToolCall(
                    name: "create_widget",
                    arguments: ["type": .string("counter"), "subject_id": .string("gym")],
                    ok: true
                ),
            ],
            turn: TalkTurnRef(threadId: "t1", turnId: "turn-1")
        )
    }

    private func journal(in directory: URL) throws -> [JournalEvent] {
        let url = directory.appending(path: "journal.jsonl")
        let text = try String(contentsOf: url, encoding: .utf8)
        return text.split(whereSeparator: \.isNewline).compactMap {
            try? FacioJSON.decoder.decode(JournalEvent.self, from: Data($0.utf8))
        }
    }
}

/// Small box so a `@Sendable` stub can report what the mouth actually saw.
private final class LockedThread: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: [TalkWireMessage] = []

    var value: [TalkWireMessage] {
        get { lock.withLock { stored } }
        set { lock.withLock { stored = newValue } }
    }
}
