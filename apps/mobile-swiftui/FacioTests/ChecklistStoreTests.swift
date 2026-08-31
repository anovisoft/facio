import XCTest
@testable import Facio

/// The checklist as it behaves on the device: a line ticked by a finger, the
/// journal that records it (step 1 of the plan reads the same journal for cue
/// hits and the late sync), «Готово», and the day the instance leaves Today.
@MainActor
final class ChecklistStoreTests: XCTestCase {
    private let now = FacioJSON.date(from: "2026-08-16T12:00:00")!

    func testTickingALineMovesTheInstanceIntoRunning() throws {
        let (store, _, _) = try makeChecklistDesk()
        store.toggleChecklistItem(widgetId: "groceries-list", itemId: "item-2")

        let widget = try XCTUnwrap(store.widget(id: "groceries-list"))
        XCTAssertEqual(ChecklistLaw.progress(of: widget.payload).done, 1)
        XCTAssertEqual(widget.status, .running)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "groceries-open" }?.status, .inProgress)
    }

    func testTickingALineIsWrittenToTheJournal() throws {
        let (store, _, directory) = try makeChecklistDesk()
        store.toggleChecklistItem(widgetId: "groceries-list", itemId: "item-1")

        let events = try journal(in: directory)
        let tick = try XCTUnwrap(events.first { $0.type == .checklistItemToggled })
        XCTAssertEqual(tick.widgetId, "groceries-list")
        XCTAssertEqual(tick.instanceId, "groceries-open")
        XCTAssertEqual(tick.payload?["item"], "item-1")
        XCTAssertEqual(tick.payload?["done"], "1")
        XCTAssertEqual(tick.payload?["total"], "3")
        XCTAssertTrue(events.contains { $0.type == .instanceStarted })
    }

    func testTickingALineThatIsNotThereWritesNothing() throws {
        let (store, _, directory) = try makeChecklistDesk()
        let before = store.snapshot
        store.toggleChecklistItem(widgetId: "groceries-list", itemId: "item-9")
        XCTAssertEqual(store.snapshot, before)
        XCTAssertTrue(try journal(in: directory).isEmpty)
    }

    func testDoneFinishesEveryLineAndClosesTheInstance() throws {
        let (store, repository, _) = try makeChecklistDesk()
        store.toggleChecklistItem(widgetId: "groceries-list", itemId: "item-1")
        store.completeChecklist(widgetId: "groceries-list")

        let widget = try XCTUnwrap(store.widget(id: "groceries-list"))
        XCTAssertEqual(widget.status, .done)
        XCTAssertTrue(ChecklistLaw.isDone(widget.payload))
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "groceries-open" }?.status, .completed)
        // Persisted, so the lid still knows after a relaunch.
        let reloaded = try XCTUnwrap(repository.loadSnapshot())
        XCTAssertEqual(reloaded.widgets.first { $0.id == "groceries-list" }?.status, .done)
    }

    func testDoneCountsTheCueHitAndTheClosedCase() throws {
        let (store, _, directory) = try makeChecklistDesk()
        store.completeChecklist(widgetId: "groceries-list")
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "groceries-cue" }?.hits.applied, 1)
        let events = try journal(in: directory)
        XCTAssertTrue(events.contains { $0.type == .cueApplied && $0.cueId == "groceries-cue" })
        XCTAssertTrue(events.contains { $0.type == .instanceCompleted })
    }

    /// Done today stays on Today, dim, until midnight; done yesterday is gone.
    func testAFinishedChecklistLeavesTodayWithTheDay() throws {
        let (store, repository, _) = try makeChecklistDesk()
        store.completeChecklist(widgetId: "groceries-list")
        XCTAssertTrue(todayIds(store).contains("groceries-list"))

        // Same desk on disk, one day later: the finished list is off Today.
        let tomorrow = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: 1, to: now))
        let later = try DeskStore(repository: repository, now: { tomorrow })
        XCTAssertFalse(todayIds(later).contains("groceries-list"))
    }

    /// Never-do #14: this type is on the lid only because the rhythm, the cue
    /// and the drift all reach it. Silence past a full cadence period is drift.
    func testAQuietChecklistGetsTheDriftCard() throws {
        let silentSince = try XCTUnwrap(Calendar.current.date(byAdding: .day, value: -21, to: now))
        let (store, _, _) = try makeChecklistDesk(doneAt: silentSince, sectionForWidget: .lifetime)
        let card = try XCTUnwrap(store.lid.driftCard)
        XCTAssertEqual(card.subjectId, "groceries")
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

    /// One practice, one checklist, one do-time cue — the smallest desk that
    /// still carries all three things never-do #14 asks for.
    private func makeChecklistDesk(
        doneAt: Date? = nil,
        sectionForWidget section: WidgetSection = .today
    ) throws -> (DeskStore, DeskRepository, URL) {
        let clock = now
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-checklist-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)

        let subject = Subject(
            id: "groceries",
            title: "список покупок",
            cadence: try Cadence.of(count: 1, period: .week),
            cueIds: ["groceries-cue"],
            instanceIds: doneAt == nil ? ["groceries-open"] : ["groceries-old", "groceries-open"]
        )
        let cue = CueLaw.addCue(
            id: "groceries-cue",
            subjectId: "groceries",
            kind: .correction,
            text: "иди после работы, не голодным"
        )
        var instances = [Instance(id: "groceries-open", subjectId: "groceries", when: clock, status: .prepared)]
        if let doneAt {
            instances.insert(
                Instance(id: "groceries-old", subjectId: "groceries", when: doneAt, status: .completed),
                at: 0
            )
        }
        let widget = Widget(
            id: "groceries-list",
            type: .checklist,
            title: "список покупок",
            payload: WidgetPayload(items: [
                ChecklistItem(id: "item-1", text: "хлеб"),
                ChecklistItem(id: "item-2", text: "молоко"),
                ChecklistItem(id: "item-3", text: "яблоки")
            ]),
            status: .ready,
            section: section,
            subjectId: "groceries",
            instanceId: "groceries-open",
            tileSize: .wide
        )
        try repository.saveSnapshot(
            DeskSnapshot(subjects: [subject], cues: [cue], instances: instances, widgets: [widget])
        )
        return (try DeskStore(repository: repository, now: { clock }), repository, directory)
    }
}
