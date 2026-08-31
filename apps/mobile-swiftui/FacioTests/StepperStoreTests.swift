import XCTest
@testable import Facio

/// The stepper on the device: beats pressed on Use, the journal that records
/// the position, «Готово», and the day the sequence leaves Today.
@MainActor
final class StepperStoreTests: XCTestCase {
    private let now = FacioJSON.date(from: "2026-08-16T12:00:00")!
    private let warmup = ["суставная разминка", "5 минут велотренажёра", "два подхода без веса"]

    func testSteppingForwardMovesTheInstanceIntoRunning() throws {
        let (store, _, _) = try makeStepperDesk()
        store.stepForward(widgetId: "warmup-stepper")

        let widget = try XCTUnwrap(store.widget(id: "warmup-stepper"))
        XCTAssertEqual(StepperLaw.position(of: widget.payload), 1)
        XCTAssertEqual(widget.status, .running)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "warmup-open" }?.status, .inProgress)
    }

    func testTheMoveIsWrittenToTheJournal() throws {
        let (store, _, directory) = try makeStepperDesk()
        store.stepForward(widgetId: "warmup-stepper")

        let events = try journal(in: directory)
        let moved = try XCTUnwrap(events.first { $0.type == .stepperMoved })
        XCTAssertEqual(moved.payload?["step"], "2")
        XCTAssertEqual(moved.payload?["total"], "3")
        XCTAssertTrue(events.contains { $0.type == .instanceStarted })
    }

    func testTheEndsDoNotWrapAndWriteNothing() throws {
        let (store, _, directory) = try makeStepperDesk()
        store.stepBack(widgetId: "warmup-stepper")
        XCTAssertEqual(StepperLaw.position(of: try XCTUnwrap(store.widget(id: "warmup-stepper")).payload), 0)
        XCTAssertTrue(try journal(in: directory).isEmpty)

        store.stepForward(widgetId: "warmup-stepper")
        store.stepForward(widgetId: "warmup-stepper")
        store.stepForward(widgetId: "warmup-stepper")
        XCTAssertEqual(StepperLaw.position(of: try XCTUnwrap(store.widget(id: "warmup-stepper")).payload), 2)
        XCTAssertEqual(try journal(in: directory).filter { $0.type == .stepperMoved }.count, 2)
    }

    func testDoneLeavesTheSequenceOnItsLastBeatAndClosesTheCase() throws {
        let (store, repository, _) = try makeStepperDesk()
        store.completeStepper(widgetId: "warmup-stepper")

        let widget = try XCTUnwrap(store.widget(id: "warmup-stepper"))
        XCTAssertEqual(widget.status, .done)
        XCTAssertTrue(StepperLaw.isLast(widget.payload))
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "warmup-open" }?.status, .completed)
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "warmup-cue" }?.hits.applied, 1)
        XCTAssertEqual(try XCTUnwrap(repository.loadSnapshot()).widgets.first?.status, .done)
    }

    func testAFinishedSequenceLeavesTodayWithTheDay() throws {
        let (store, repository, _) = try makeStepperDesk()
        store.completeStepper(widgetId: "warmup-stepper")
        XCTAssertTrue(todayIds(store).contains("warmup-stepper"))

        let tomorrow = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: 1, to: now))
        let later = try DeskStore(repository: repository, now: { tomorrow })
        XCTAssertFalse(todayIds(later).contains("warmup-stepper"))
    }

    func testAQuietStepperGetsTheDriftCard() throws {
        let silentSince = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: -14, to: now))
        let (store, _, _) = try makeStepperDesk(doneAt: silentSince, section: .lifetime)
        let card = try XCTUnwrap(store.lid.driftCard)
        XCTAssertEqual(card.subjectId, "warmup")
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

    private func makeStepperDesk(
        doneAt: Date? = nil,
        section: WidgetSection = .today
    ) throws -> (DeskStore, DeskRepository, URL) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-stepper-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)

        let subject = Subject(
            id: "warmup",
            title: "разминка",
            cadence: try Cadence.of(count: 2, period: .week),
            cueIds: ["warmup-cue"],
            instanceIds: doneAt == nil ? ["warmup-open"] : ["warmup-old", "warmup-open"]
        )
        let cue = CueLaw.addCue(
            id: "warmup-cue",
            subjectId: "warmup",
            kind: .correction,
            text: "не тяни на холодную"
        )
        var instances = [Instance(id: "warmup-open", subjectId: "warmup", when: now, status: .prepared)]
        if let doneAt {
            instances.insert(
                Instance(id: "warmup-old", subjectId: "warmup", when: doneAt, status: .completed),
                at: 0
            )
        }
        let widget = Widget(
            id: "warmup-stepper",
            type: .stepper,
            title: "разминка",
            payload: WidgetPayload(beats: warmup, current: 0),
            status: .ready,
            section: section,
            subjectId: "warmup",
            instanceId: "warmup-open",
            tileSize: .wide
        )
        try repository.saveSnapshot(
            DeskSnapshot(subjects: [subject], cues: [cue], instances: instances, widgets: [widget])
        )
        return (try DeskStore(repository: repository, now: { self.now }), repository, directory)
    }
}
