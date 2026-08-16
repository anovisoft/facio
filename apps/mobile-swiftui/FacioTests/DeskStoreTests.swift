import XCTest
@testable import Facio

@MainActor
final class DeskStoreTests: XCTestCase {
    func testEditReminderLatestByWritesWindowAndPersists() throws {
        let (store, repository) = try makeDesk()
        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy.hour, 19)

        store.editReminderLatestBy(widgetId: "bike-reminder", latestBy: ClockTime(hour: 20, minute: 0))

        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy.hour, 20)
        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy.minute, 0)
        let widget = try XCTUnwrap(store.widget(id: "bike-reminder"))
        XCTAssertEqual(ReminderClock.clock(from: try XCTUnwrap(widget.when)).hour, 20)

        let reloaded = try XCTUnwrap(repository.loadSnapshot())
        XCTAssertEqual(reloaded.subjects.first { $0.id == "bike" }?.window?.latestBy.hour, 20)
    }

    func testEditReminderLatestByWritesEvenWhenDone() throws {
        let (store, _) = try makeDesk()
        store.completeReminder(widgetId: "bike-reminder")
        store.editReminderLatestBy(widgetId: "bike-reminder", latestBy: ClockTime(hour: 18, minute: 30))
        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy, ClockTime(hour: 18, minute: 30))
    }

    func testTickCounterWritesWidgetAndInstanceTogether() throws {
        let (store, _) = try makeDesk()
        store.tickCounter(widgetId: "push-ups-counter", delta: 1)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 29)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .running)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "push-ups-open" }?.status, .inProgress)
    }

    func testMarkCueSurfacedOncePerPlacePerDay() throws {
        let (store, _) = try makeDesk()
        let before = store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced ?? 0
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, before + 1)
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "use")
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, before + 2)
    }

    func testMarkCueSurfacedSurvivesRelaunch() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeDesk(now: now)
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        let afterFirst = store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced
        let reloaded = try DeskStore(repository: repository, now: { now })
        reloaded.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        XCTAssertEqual(reloaded.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, afterFirst)
    }

    func testCompleteReminderDropsAlarm() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        XCTAssertFalse(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
        store.completeReminder(widgetId: "bike-reminder")
        XCTAssertTrue(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
    }

    private func makeDesk(now: Date = Date()) throws -> (DeskStore, DeskRepository) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-desk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        return (try DeskStore(repository: repository, now: { now }), repository)
    }
}
