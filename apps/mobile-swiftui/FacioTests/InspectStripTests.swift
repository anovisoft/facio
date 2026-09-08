import XCTest
@testable import Facio

/// Q34 on the second surface: Inspect's day strip is a queue of occurrences,
/// and an hour is not one of them. The carousel learned this in R16; this is
/// the tail it left on Inspect, filtered by the same law and not by a second
/// copy of it.
@MainActor
final class InspectStripTests: XCTestCase {
    func testThreeChecksAndAnHourGiveThreeChips() throws {
        let store = try makeDesk(checksADay: 3, withReminder: true)
        let listed = store.occurrenceInstances(for: subjectId)

        XCTAssertEqual(store.instances(for: subjectId).count, 4, "the hour is on the desk")
        XCTAssertEqual(listed.count, 3, "and it is not one of the three checks")
        XCTAssertFalse(listed.contains { $0.id == hourInstanceId })
    }

    func testAPracticeWhoseOnlyCaseIsTheAlarmKeepsIt() throws {
        let store = try makeAlarmOnlyDesk()
        let listed = store.occurrenceInstances(for: "sauna")

        // R11's exception, read out loud: the bike's alarm is its ride, and an
        // empty strip is worse than an honest one.
        XCTAssertEqual(listed.count, 1)
        XCTAssertEqual(listed.first?.id, "sauna-hour")
    }

    func testTheSeededBikeListsTheRideAndNotItsAlarm() throws {
        let store = try makeDesk(checksADay: 3, withReminder: true)
        let listed = store.occurrenceInstances(for: "bike")

        // The bike does have another case — the 21-day silence — so the hour
        // steps out of the queue here.
        XCTAssertEqual(listed.map(\.id), ["bike-silent"])
    }

    func testThePickedChipSurvivesTheFilter() throws {
        let store = try makeDesk(checksADay: 3, withReminder: true)
        let listed = store.occurrenceInstances(for: subjectId)
        let picked = try XCTUnwrap(listed.first)

        let selected = InspectScreen.selection(
            in: listed,
            preferring: picked.id,
            arrivedOn: try XCTUnwrap(listed.last).id
        )
        XCTAssertEqual(selected?.id, picked.id)
    }

    func testArrivingOnTheHourStillLandsOnACase() throws {
        let store = try makeDesk(checksADay: 3, withReminder: true)
        let listed = store.occurrenceInstances(for: subjectId)

        // A glance tile hands Inspect the case its reminder stands on. The slot
        // is gone from the strip; the loud date must not go with it.
        let selected = InspectScreen.selection(
            in: listed,
            preferring: hourInstanceId,
            arrivedOn: hourInstanceId
        )
        XCTAssertNotNil(selected)
        XCTAssertTrue(listed.contains { $0.id == selected?.id })
    }

    // MARK: -

    private let subjectId = "upwork"
    private let hourInstanceId = "upwork-hour"

    private var stamp: Date {
        FacioJSON.date(from: "2026-08-30T09:00:00") ?? Date()
    }

    private func store(from snapshot: DeskSnapshot) throws -> DeskStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-inspect-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(snapshot)
        let now = stamp
        return try DeskStore(repository: repository, now: { now })
    }

    /// A practice that promises `checksADay` checks and states exactly that
    /// many hours — the shape R16 groups, so the hours really do land on the
    /// occurrences and the reminder is the only case left over.
    private func makeDesk(checksADay: Int, withReminder: Bool) throws -> DeskStore {
        let now = stamp
        var snapshot = try SeedFactory.buildSeed(now: now)
        let hours = [10, 15, 18].prefix(checksADay).map { ClockTime(hour: $0, minute: 0) }
        let window = TimeWindow(hours: Array(hours))
        snapshot.subjects.append(
            Subject(
                id: subjectId,
                title: "проверить upwork",
                cadence: try Cadence.of(count: checksADay, period: .day),
                window: window,
                instanceIds: ["upwork-open"]
            )
        )
        snapshot.instances.append(
            Instance(id: "upwork-open", subjectId: subjectId, when: now, status: .prepared)
        )
        snapshot.widgets.append(
            Widget(
                id: "upwork-tick",
                type: .tick,
                title: "проверить upwork",
                payload: WidgetPayload(done: false),
                status: .ready,
                section: .today,
                subjectId: subjectId,
                instanceId: "upwork-open",
                tileSize: .compact
            )
        )
        if withReminder {
            let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
            snapshot.instances.append(
                Instance(id: hourInstanceId, subjectId: subjectId, when: fireAt, status: .prepared)
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
                    subjectId: subjectId,
                    instanceId: hourInstanceId,
                    tileSize: .wide
                )
            )
        }
        return try store(from: snapshot)
    }

    /// A practice that has never run: one reminder, one case, and that case is
    /// the hour.
    private func makeAlarmOnlyDesk() throws -> DeskStore {
        let now = stamp
        var snapshot = try SeedFactory.buildSeed(now: now)
        let window = ReminderClock.windowFromClosing(ClockTime(hour: 22, minute: 0))
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
        snapshot.subjects.append(
            Subject(
                id: "sauna",
                title: "баня",
                cadence: try Cadence.of(count: 1, period: .week),
                window: window,
                instanceIds: ["sauna-hour"]
            )
        )
        snapshot.instances.append(
            Instance(id: "sauna-hour", subjectId: "sauna", when: fireAt, status: .prepared)
        )
        snapshot.widgets.append(
            Widget(
                id: "sauna-reminder",
                type: .reminder,
                title: "баня",
                payload: WidgetPayload(fireAt: fireAt),
                status: .ready,
                when: fireAt,
                section: .today,
                subjectId: "sauna",
                instanceId: "sauna-hour",
                tileSize: .wide
            )
        )
        return try store(from: snapshot)
    }
}
