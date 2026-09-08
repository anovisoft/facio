import XCTest
@testable import Facio

/// The timer on the device: start / pause on the tile, the journal that
/// records the seconds it produced, «Готово», and the day the sitting leaves
/// Today. Same four locks as the checklist (never-do #14).
@MainActor
final class TimerStoreTests: XCTestCase {
    private let start = FacioJSON.date(from: "2026-08-16T12:00:00")!
    private let tenMinutes = 600

    func testStartingTheRunMovesTheInstanceIntoRunning() throws {
        var clock = start
        let (store, _, _) = try makeTimerDesk(now: { clock })
        store.toggleTimerRun(widgetId: "meditation-timer")

        let widget = try XCTUnwrap(store.widget(id: "meditation-timer"))
        XCTAssertTrue(TimerLaw.isRunning(widget.payload))
        XCTAssertEqual(widget.status, .running)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "meditation-open" }?.status, .inProgress)

        clock = start.addingTimeInterval(120)
        XCTAssertEqual(TimerLaw.remaining(widget.payload, now: clock), tenMinutes - 120)
    }

    func testPausingBanksTheSecondsAndWritesThemToTheJournal() throws {
        var clock = start
        let (store, _, directory) = try makeTimerDesk(now: { clock })
        store.toggleTimerRun(widgetId: "meditation-timer")
        clock = start.addingTimeInterval(180)
        store.toggleTimerRun(widgetId: "meditation-timer")

        let widget = try XCTUnwrap(store.widget(id: "meditation-timer"))
        XCTAssertFalse(TimerLaw.isRunning(widget.payload))
        XCTAssertEqual(widget.payload.elapsed, 180)

        let events = try journal(in: directory)
        XCTAssertTrue(events.contains { $0.type == .timerStarted })
        let paused = try XCTUnwrap(events.first { $0.type == .timerPaused })
        XCTAssertEqual(paused.payload?["elapsed"], "180")
        XCTAssertEqual(paused.widgetId, "meditation-timer")
    }

    /// The run survives a relaunch: what is on disk is the moment it began,
    /// not a number somebody has to keep ticking.
    func testARunSurvivesARelaunch() throws {
        var clock = start
        let (store, repository, _) = try makeTimerDesk(now: { clock })
        store.toggleTimerRun(widgetId: "meditation-timer")

        clock = start.addingTimeInterval(240)
        let reopened = try DeskStore(repository: repository, now: { clock })
        let widget = try XCTUnwrap(reopened.widget(id: "meditation-timer"))
        XCTAssertTrue(TimerLaw.isRunning(widget.payload))
        XCTAssertEqual(TimerLaw.elapsed(widget.payload, now: clock), 240)
    }

    func testResetGoesBackToTheFullLengthWithoutClosingTheCase() throws {
        var clock = start
        let (store, _, _) = try makeTimerDesk(now: { clock })
        store.toggleTimerRun(widgetId: "meditation-timer")
        clock = start.addingTimeInterval(90)
        store.resetTimer(widgetId: "meditation-timer")

        let widget = try XCTUnwrap(store.widget(id: "meditation-timer"))
        XCTAssertEqual(widget.payload.seconds, tenMinutes)
        XCTAssertEqual(TimerLaw.remaining(widget.payload, now: clock), tenMinutes)
        XCTAssertNotEqual(widget.status, .done)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "meditation-open" }?.status, .inProgress)
    }

    func testDoneStopsTheRunAndClosesTheCase() throws {
        var clock = start
        let (store, _, directory) = try makeTimerDesk(now: { clock })
        store.toggleTimerRun(widgetId: "meditation-timer")
        clock = start.addingTimeInterval(600)
        store.completeTimer(widgetId: "meditation-timer")

        let widget = try XCTUnwrap(store.widget(id: "meditation-timer"))
        XCTAssertEqual(widget.status, .done)
        XCTAssertFalse(TimerLaw.isRunning(widget.payload))
        XCTAssertEqual(widget.payload.elapsed, 600)
        // A closed case does not keep counting.
        XCTAssertEqual(TimerLaw.elapsed(widget.payload, now: clock.addingTimeInterval(3_600)), 600)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "meditation-open" }?.status, .completed)
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "meditation-cue" }?.hits.applied, 1)
        let events = try journal(in: directory)
        XCTAssertTrue(events.contains { $0.type == .instanceCompleted && $0.payload?["elapsed"] == "600" })
    }

    /// The finished **sitting** leaves Today with the day; the practice does not.
    ///
    /// This used to assert that the tile was gone from Today altogether on the
    /// next day, and that was the hole, not the rule: медитация is `1×/day`, so
    /// day two owes a sitting. The desk wrote none — a once-a-day practice
    /// closed on day one simply never came back, and three days later it was
    /// handed a drift card for silence it had been given no tile to break.
    ///
    /// What must be true is narrower: yesterday's case is closed and stays on
    /// yesterday, and the tile that comes back is a **new, empty** sitting.
    func testAFinishedSittingLeavesTodayAndTheNextDayGetsItsOwn() throws {
        var clock = start
        let (store, repository, _) = try makeTimerDesk(now: { clock })
        store.completeTimer(widgetId: "meditation-timer")
        XCTAssertTrue(todayIds(store).contains("meditation-timer"))

        clock = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: 1, to: start))
        let later = try DeskStore(repository: repository, now: { clock })
        XCTAssertTrue(todayIds(later).contains("meditation-timer"))

        let widget = try XCTUnwrap(later.widget(id: "meditation-timer"))
        XCTAssertEqual(widget.status, .ready)
        XCTAssertNotEqual(widget.instanceId, "meditation-open")
        XCTAssertNil(widget.payload.elapsed)
        XCTAssertFalse(TimerLaw.isRunning(widget.payload))
        // Yesterday's sitting is untouched: closed, and still on yesterday.
        let closed = try XCTUnwrap(later.snapshot.instances.first { $0.id == "meditation-open" })
        XCTAssertEqual(closed.status, .completed)
        XCTAssertTrue(SlotLaw.isSameDay(closed.when, start))
    }

    func testAQuietTimerGetsTheDriftCard() throws {
        let silentSince = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: -6, to: start))
        let (store, _, _) = try makeTimerDesk(now: { self.start }, doneAt: silentSince, section: .lifetime)
        let card = try XCTUnwrap(store.lid.driftCard)
        XCTAssertEqual(card.subjectId, "meditation")
        XCTAssertTrue(store.surfaces(card))
    }

    // MARK: - Fixtures

    private func todayIds(_ store: DeskStore) -> [String] {
        store.lid.today.compactMap { item in
            if case .widget(_, let widget) = item { return widget.id }
            return nil
        }
    }

    private func journal(in directory: URL) throws -> [JournalEvent] {
        let url = directory.appending(path: "journal.jsonl")
        guard let data = try? Data(contentsOf: url), let text = String(data: data, encoding: .utf8) else {
            return []
        }
        return text.split(whereSeparator: \.isNewline).compactMap {
            try? FacioJSON.decoder.decode(JournalEvent.self, from: Data($0.utf8))
        }
    }

    private func makeTimerDesk(
        now: @escaping () -> Date,
        doneAt: Date? = nil,
        section: WidgetSection = .today
    ) throws -> (DeskStore, DeskRepository, URL) {
        let stamp = now()
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-timer-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)

        let subject = Subject(
            id: "meditation",
            title: "медитация",
            cadence: try Cadence.of(count: 1, period: .day),
            cueIds: ["meditation-cue"],
            instanceIds: doneAt == nil ? ["meditation-open"] : ["meditation-old", "meditation-open"]
        )
        let cue = CueLaw.addCue(
            id: "meditation-cue",
            subjectId: "meditation",
            kind: .correction,
            text: "сядь ровно, дыши носом"
        )
        var instances = [Instance(id: "meditation-open", subjectId: "meditation", when: stamp, status: .prepared)]
        if let doneAt {
            instances.insert(
                Instance(id: "meditation-old", subjectId: "meditation", when: doneAt, status: .completed),
                at: 0
            )
        }
        let widget = Widget(
            id: "meditation-timer",
            type: .timer,
            title: "медитация",
            payload: WidgetPayload(seconds: tenMinutes, elapsed: 0),
            status: .ready,
            section: section,
            subjectId: "meditation",
            instanceId: "meditation-open",
            tileSize: .compact
        )
        try repository.saveSnapshot(
            DeskSnapshot(subjects: [subject], cues: [cue], instances: instances, widgets: [widget])
        )
        return (try DeskStore(repository: repository, now: now), repository, directory)
    }
}
