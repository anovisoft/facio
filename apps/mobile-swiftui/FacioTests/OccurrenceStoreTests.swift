import XCTest
@testable import Facio

/// Q34, the half the lid owns: a practice that promised seven checks a day
/// gets seven cases and seven tiles, and each of them is ticked on its own.
@MainActor
final class OccurrenceStoreTests: XCTestCase {
    func testSevenChecksADayLandAsSevenTilesOnToday() throws {
        let (store, _) = try makeUpworkDesk()
        let today = todayWidgets(store).filter { $0.subjectId == "upwork" }
        XCTAssertEqual(today.count, 7)
        XCTAssertEqual(Set(today.map(\.instanceId)).count, 7)
        XCTAssertTrue(today.allSatisfy { $0.type == .tick && $0.status == .ready })
        XCTAssertEqual(store.snapshot.instances.filter { $0.subjectId == "upwork" }.count, 7)
    }

    func testTheSixthDoesNotGoOutBecauseTheFirstWasTicked() throws {
        let (store, _) = try makeUpworkDesk()
        let tiles = todayWidgets(store).filter { $0.subjectId == "upwork" }
        store.toggleTick(widgetId: try XCTUnwrap(tiles.first).id)
        let after = store.snapshot.widgets.filter { $0.subjectId == "upwork" }
        XCTAssertEqual(after.count, 7)
        XCTAssertEqual(after.filter { $0.status == .done }.count, 1)
        XCTAssertEqual(after.filter { $0.status != .done }.count, 6)
    }

    func testAFinishedCheckDoesNotWriteAnEighth() throws {
        let (store, _) = try makeUpworkDesk()
        for widget in store.snapshot.widgets where widget.subjectId == "upwork" {
            store.toggleTick(widgetId: widget.id)
        }
        // All seven closed, and the top-up runs again: still seven.
        store.ensureOccurrences()
        XCTAssertEqual(store.snapshot.widgets.filter { $0.subjectId == "upwork" }.count, 7)
        XCTAssertEqual(store.snapshot.instances.filter { $0.subjectId == "upwork" }.count, 7)
    }

    func testTheTopUpIsIdempotent() throws {
        let (store, _) = try makeUpworkDesk()
        let before = store.snapshot
        store.ensureOccurrences()
        store.ensureOccurrences()
        XCTAssertEqual(store.snapshot, before)
    }

    func testTheTopUpSurvivesARelaunchWithoutMultiplying() throws {
        let (store, repository) = try makeUpworkDesk()
        XCTAssertEqual(store.snapshot.widgets.filter { $0.subjectId == "upwork" }.count, 7)
        let reopened = try DeskStore(repository: repository, now: { self.stamp })
        XCTAssertEqual(reopened.snapshot.widgets.filter { $0.subjectId == "upwork" }.count, 7)
    }

    func testTheReminderTileIsNotMultipliedWithTheChecks() throws {
        let (store, _) = try makeUpworkDesk(withReminder: true)
        let reminders = store.snapshot.widgets.filter {
            $0.subjectId == "upwork" && $0.type == .reminder
        }
        // The hours live in one window, not in one case per hour.
        XCTAssertEqual(reminders.count, 1)
        XCTAssertEqual(store.windowFor(subjectId: "upwork")?.hours.count, 7)
        // And the reminder's own case is not one of the seven checks.
        let ticks = store.snapshot.widgets.filter { $0.subjectId == "upwork" && $0.type == .tick }
        XCTAssertEqual(ticks.count, 7)
    }

    func testAWeeklyPracticeIsLeftAlone() throws {
        let (store, _) = try makeUpworkDesk()
        XCTAssertEqual(store.snapshot.widgets.filter { $0.subjectId == "bike" }.count, 1)
        XCTAssertEqual(store.snapshot.instances.filter { $0.subjectId == "push-ups" }.count, 1)
    }

    // MARK: -

    private func todayWidgets(_ store: DeskStore) -> [Widget] {
        store.lid.today.compactMap { item in
            if case .widget(_, let widget) = item { return widget }
            return nil
        }
    }

    private var stamp: Date {
        FacioJSON.date(from: "2026-08-30T09:00:00") ?? Date()
    }

    private func makeUpworkDesk(withReminder: Bool = false) throws -> (DeskStore, DeskRepository) {
        let now = stamp
        var snapshot = try SeedFactory.buildSeed(now: now)
        let hours = [10, 12, 15, 18, 21, 22].map { ClockTime(hour: $0, minute: 0) }
            + [ClockTime(hour: 16, minute: 30)]
        snapshot.subjects.append(
            Subject(
                id: "upwork",
                title: "проверить upwork",
                cadence: try Cadence.of(count: 7, period: .day),
                window: TimeWindow(hours: hours),
                instanceIds: ["upwork-open"]
            )
        )
        snapshot.instances.append(
            Instance(id: "upwork-open", subjectId: "upwork", when: now, status: .prepared)
        )
        snapshot.widgets.append(
            Widget(
                id: "upwork-tick",
                type: .tick,
                title: "проверить upwork",
                payload: WidgetPayload(done: false),
                status: .ready,
                section: .today,
                subjectId: "upwork",
                instanceId: "upwork-open",
                tileSize: .compact
            )
        )
        if withReminder {
            let fireAt = ReminderClock.reminderFireAt(
                window: TimeWindow(hours: hours),
                on: now
            )
            snapshot.instances.append(
                Instance(id: "upwork-hour", subjectId: "upwork", when: fireAt, status: .prepared)
            )
            snapshot.widgets.append(
                Widget(
                    id: "upwork-reminder",
                    type: .reminder,
                    title: "проверить upwork",
                    payload: WidgetPayload(fireAt: fireAt),
                    status: .ready,
                    when: fireAt,
                    section: .today,
                    subjectId: "upwork",
                    instanceId: "upwork-hour",
                    tileSize: .wide
                )
            )
        }
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-occurrences-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(snapshot)
        return (try DeskStore(repository: repository, now: { now }), repository)
    }
}
