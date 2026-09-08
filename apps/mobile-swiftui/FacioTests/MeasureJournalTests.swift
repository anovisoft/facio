import XCTest
@testable import Facio

/// The two events step 7 needed and the journal did not have.
///
/// Both are about things that leave no other trace: a turn that only talked
/// writes nothing at all, and the drift ladder remembers *that* it asked
/// (`drift_asked_at`) but never how late the ask came. Without these two the
/// kill criteria — «was a cue ever read at do-time», «was drift caught before
/// the failure» — are not questions the device can answer about itself.
@MainActor
final class MeasureJournalTests: XCTestCase {
    private let stamp = FacioJSON.date(from: "2026-08-16T12:00:00")!

    // MARK: - a turn of the mouth

    func testATurnThatChangedTheDeskIsWrittenAsBuilt() throws {
        let (store, _, directory) = try makeDesk()
        store.applyTalk(
            try gymDesk(from: store.snapshot),
            toolCalls: [
                TalkToolCall(
                    name: "create_widget",
                    arguments: ["type": .string("counter")],
                    ok: true
                )
            ],
            turn: TalkTurnRef(threadId: "t1", turnId: "turn-1")
        )
        let turn = try XCTUnwrap(journal(in: directory).last { $0.type == .talkTurn })
        XCTAssertEqual(turn.payload?["mutated"], "true")
        XCTAssertEqual(turn.payload?["tools"], "1")
    }

    /// The turn the share is actually about: the mouth answered, nothing landed
    /// on the desk. It has to be countable, and it writes no other event.
    func testATurnThatOnlyTalkedIsStillWrittenDown() throws {
        let (store, _, directory) = try makeDesk()
        store.applyTalk(store.snapshot, toolCalls: [], turn: nil)

        let turns = journal(in: directory).filter { $0.type == .talkTurn }
        XCTAssertEqual(turns.count, 1)
        XCTAssertEqual(turns.first?.payload?["mutated"], "false")
        XCTAssertNil(store.undoableTurn, "nothing changed, so there is nothing to take back")
    }

    /// The share that Q25 asks for, end to end: three turns in, one of them
    /// built something.
    func testTheShareIsReadableBackOutOfTheJournal() throws {
        let (store, _, directory) = try makeDesk()
        store.applyTalk(store.snapshot, toolCalls: [], turn: nil)
        store.applyTalk(store.snapshot, toolCalls: [], turn: nil)
        store.applyTalk(
            try gymDesk(from: store.snapshot),
            toolCalls: [],
            turn: TalkTurnRef(threadId: "t1", turnId: "turn-1")
        )

        let report = MeasureLaw.report(journal: journal(in: directory), desk: store.snapshot, now: stamp)
        XCTAssertEqual(report.talkTurns, 3)
        XCTAssertEqual(report.talkTurnsThatBuilt, 1)
        XCTAssertEqual(try XCTUnwrap(report.mechanicShare), 1.0 / 3.0, accuracy: 0.0001)
    }

    // MARK: - a drift card that reached the lid

    func testTheCardIsWrittenOnceWithTheSilenceThatEarnedIt() throws {
        let (store, _, directory) = try makeDesk()
        let card = DriftCard(subjectId: "bike", silentDays: 21, offer: .moveToToday)

        store.markDriftSurfaced(card)

        let events = journal(in: directory).filter { $0.type == .driftSurfaced }
        XCTAssertEqual(events.count, 1)
        XCTAssertEqual(events.first?.subjectId, "bike")
        XCTAssertEqual(events.first?.payload?["silent_days"], "21")
        XCTAssertEqual(events.first?.payload?["offer"], "move_to_today")
    }

    /// The card sits on screen for as long as the person leaves it there and
    /// `onAppear` fires on every scroll. Without the latch the journal would
    /// count redraws and every measurement over it would be fiction.
    func testScrollingPastTheCardDoesNotCountASecondAsk() throws {
        let (store, repository, directory) = try makeDesk()
        let card = DriftCard(subjectId: "bike", silentDays: 21, offer: .moveToToday)

        for _ in 0..<5 { store.markDriftSurfaced(card) }
        XCTAssertEqual(journal(in: directory).filter { $0.type == .driftSurfaced }.count, 1)

        // And the latch survives a relaunch — it is read back off the journal,
        // not held in memory, so the same day cannot be counted twice.
        let reopened = try DeskStore(repository: repository, now: { self.stamp })
        reopened.markDriftSurfaced(card)
        XCTAssertEqual(journal(in: directory).filter { $0.type == .driftSurfaced }.count, 1)
    }

    func testANewDayIsANewAsk() throws {
        let (store, repository, directory) = try makeDesk()
        let card = DriftCard(subjectId: "bike", silentDays: 21, offer: .moveToToday)
        store.markDriftSurfaced(card)

        let tomorrow = SlotLaw.dayCalendar.date(byAdding: .day, value: 1, to: stamp)!
        let next = try DeskStore(repository: repository, now: { tomorrow })
        next.markDriftSurfaced(DriftCard(subjectId: "bike", silentDays: 22, offer: .moveToToday))

        let events = journal(in: directory).filter { $0.type == .driftSurfaced }
        XCTAssertEqual(events.count, 2)
        XCTAssertEqual(events.map { $0.payload?["silent_days"] }, ["21", "22"])
    }

    func testTwoPracticesOnOneDayAreTwoAsks() throws {
        let (store, _, directory) = try makeDesk()
        store.markDriftSurfaced(DriftCard(subjectId: "bike", silentDays: 21, offer: .moveToToday))
        store.markDriftSurfaced(DriftCard(subjectId: "push-ups", silentDays: 9, offer: .onceAWeek))

        XCTAssertEqual(journal(in: directory).filter { $0.type == .driftSurfaced }.count, 2)
    }

    // MARK: - Helpers

    private func makeDesk() throws -> (DeskStore, DeskRepository, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-measure-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(SeedFactory.buildSeed(now: stamp))
        return (try DeskStore(repository: repository, now: { self.stamp }), repository, directory)
    }

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

    private func journal(in directory: URL) -> [JournalEvent] {
        DeskRepository(directory: directory).journal()
    }
}
