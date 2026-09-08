import XCTest
@testable import Facio

/// R18, part B: the hours of a grouped practice are added, moved and dropped by
/// hand from the carousel.
///
/// The invariant every one of these tests re-checks is the one R16 hangs on —
/// **as many stated hours as there are checks**. Break it and the hours stop
/// landing on the occurrences, the group goes back to anonymous squares, and
/// R17 hands the reminder tile back. So the count is asserted after every
/// single operation, not once at the end.
@MainActor
final class OccurrenceHourTests: XCTestCase {
    // MARK: - what the carousel is allowed to edit

    func testAPracticeStatingItsHoursOffersThemForEditing() throws {
        let store = try makeUpwork()
        let group = try XCTUnwrap(store.hourGroup(subjectId: "upwork"))
        XCTAssertEqual(group.total, 3)
        XCTAssertEqual(group.window.hours, hours)
        assertHoursMatchOccurrences(store)
    }

    func testAnOrdinaryPracticeIsNotTouched() throws {
        let store = try makeUpwork()
        // One check a day is not a group, so `+` clones as it always did.
        XCTAssertNil(store.hourGroup(subjectId: "vegetables"))
        XCTAssertNil(store.hourGroup(subjectId: "push-ups"))
        XCTAssertNotNil(store.addInstance(subjectId: "push-ups"))
    }

    /// The bug itself: `+` used to stamp «сейчас» on a new check, twice in a
    /// row, and the hours stopped matching the checks.
    func testPlusRefusesToCloneAGroupedPracticeWithoutAnHour() throws {
        let store = try makeUpwork()
        XCTAssertNil(store.addInstance(subjectId: "upwork"))
        XCTAssertNil(store.addInstance(subjectId: "upwork"))
        XCTAssertEqual(occurrences(store).count, 3)
        assertHoursMatchOccurrences(store)
    }

    // MARK: - add

    func testAddingAnHourAddsTheCheckThatGoesWithIt() throws {
        let store = try makeUpwork()
        let created = try XCTUnwrap(store.addHour(subjectId: "upwork", clock: ClockTime(hour: 19, minute: 30)))
        let window = try XCTUnwrap(store.windowFor(subjectId: "upwork"))
        XCTAssertEqual(window.hours.count, 4)
        XCTAssertTrue(window.hours.contains(ClockTime(hour: 19, minute: 30)))
        XCTAssertEqual(occurrences(store).count, 4)
        // The new case wears the hour it was created for, not «сейчас».
        let made = try XCTUnwrap(store.snapshot.instances.first { $0.id == created })
        XCTAssertEqual(ReminderClock.clock(from: made.when), ClockTime(hour: 19, minute: 30))
        assertHoursMatchOccurrences(store)
    }

    /// The promise counts one more too. `SlotLaw.occurrencesPromised` is what
    /// the top-up reads to decide how many checks a day owes, and R16 lays the
    /// hours onto the cases only while that number and the window agree — so
    /// raising the hours without raising the count would arm a group that goes
    /// anonymous the moment it is rebuilt.
    ///
    /// (Rolling a grouped day over to the *next* day is R16's own gap and not
    /// this slice's: `SeedFactory.occurrenceTemplate` looks for a widget bound
    /// to a case on that very day, and a fresh day has none. What is asserted
    /// here is the promise, which is the half R18 owns.)
    func testAddingAnHourRaisesThePromiseWithIt() throws {
        let store = try makeUpwork()
        let subject = try XCTUnwrap(store.subject(id: "upwork"))
        XCTAssertEqual(SlotLaw.occurrencesPromised(subject), 3)

        store.addHour(subjectId: "upwork", clock: ClockTime(hour: 19, minute: 30))
        let raised = try XCTUnwrap(store.subject(id: "upwork"))
        XCTAssertEqual(raised.cadence.count, 4)
        XCTAssertEqual(SlotLaw.occurrencesPromised(raised), 4)
        XCTAssertEqual(SlotLaw.occurrencesPromised(raised), try XCTUnwrap(raised.window).hours.count)
        // And the top-up, run again on the same day, writes nothing more.
        store.ensureOccurrences()
        XCTAssertEqual(occurrences(store).count, 4)
        assertHoursMatchOccurrences(store)
    }

    func testDroppingAnHourLowersThePromiseWithIt() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        store.dropHour(subjectId: "upwork", instanceId: slot.instanceId)
        let lowered = try XCTUnwrap(store.subject(id: "upwork"))
        XCTAssertEqual(SlotLaw.occurrencesPromised(lowered), 2)
        XCTAssertEqual(SlotLaw.occurrencesPromised(lowered), try XCTUnwrap(lowered.window).hours.count)
        store.ensureOccurrences()
        XCTAssertEqual(occurrences(store).count, 2)
        assertHoursMatchOccurrences(store)
    }

    func testAnHourAlreadyStandingIsNotAddedTwice() throws {
        let store = try makeUpwork()
        let before = store.snapshot
        let landed = store.addHour(subjectId: "upwork", clock: ClockTime(hour: 12, minute: 0))
        XCTAssertEqual(store.snapshot, before)
        XCTAssertEqual(occurrences(store).count, 3)
        // It hands back the check already standing on that hour, so the
        // carousel moves to it instead of quietly doing nothing.
        let standing = try XCTUnwrap(landed)
        let instance = try XCTUnwrap(store.snapshot.instances.first { $0.id == standing })
        XCTAssertEqual(ReminderClock.clock(from: instance.when), ClockTime(hour: 12, minute: 0))
        assertHoursMatchOccurrences(store)
    }

    func testAddingAnHourSetsAnAlarmForIt() throws {
        let store = try makeUpwork()
        let before = alarmHours(store)
        XCTAssertEqual(before, hours)
        store.addHour(subjectId: "upwork", clock: ClockTime(hour: 19, minute: 30))
        XCTAssertEqual(alarmHours(store), (hours + [ClockTime(hour: 19, minute: 30)]).sorted())
    }

    // MARK: - move

    func testMovingASlotMovesTheHourInTheWindowAndTheCaseWithIt() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        XCTAssertTrue(store.moveHour(subjectId: "upwork", instanceId: slot.instanceId, to: ClockTime(hour: 13, minute: 15)))

        let window = try XCTUnwrap(store.windowFor(subjectId: "upwork"))
        XCTAssertEqual(window.hours, [ClockTime(hour: 10, minute: 0), ClockTime(hour: 13, minute: 15), ClockTime(hour: 15, minute: 0)])
        let moved = try XCTUnwrap(store.snapshot.instances.first { $0.id == slot.instanceId })
        XCTAssertEqual(ReminderClock.clock(from: moved.when), ClockTime(hour: 13, minute: 15))
        // The other two did not shuffle.
        XCTAssertEqual(occurrenceHours(store), window.hours)
        assertHoursMatchOccurrences(store)
    }

    /// Moving one hour past another re-sorts the row; the hours must follow the
    /// cases, not be handed out again in a different order.
    func testMovingASlotPastItsNeighbourKeepsEveryCheckOnItsOwnHour() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 15, minute: 0)))
        XCTAssertTrue(store.moveHour(subjectId: "upwork", instanceId: slot.instanceId, to: ClockTime(hour: 9, minute: 0)))
        let moved = try XCTUnwrap(store.snapshot.instances.first { $0.id == slot.instanceId })
        XCTAssertEqual(ReminderClock.clock(from: moved.when), ClockTime(hour: 9, minute: 0))
        XCTAssertEqual(occurrenceHours(store), [ClockTime(hour: 9, minute: 0), ClockTime(hour: 10, minute: 0), ClockTime(hour: 12, minute: 0)])
        assertHoursMatchOccurrences(store)
    }

    func testMovingOntoAnHourAlreadyStandingIsRefused() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        let before = store.snapshot
        XCTAssertFalse(store.moveHour(subjectId: "upwork", instanceId: slot.instanceId, to: ClockTime(hour: 15, minute: 0)))
        XCTAssertEqual(store.snapshot, before)
        assertHoursMatchOccurrences(store)
    }

    func testMovingAnHourMovesItsAlarm() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        store.moveHour(subjectId: "upwork", instanceId: slot.instanceId, to: ClockTime(hour: 13, minute: 15))
        XCTAssertEqual(
            alarmHours(store),
            [ClockTime(hour: 10, minute: 0), ClockTime(hour: 13, minute: 15), ClockTime(hour: 15, minute: 0)]
        )
    }

    // MARK: - drop

    func testDroppingAnHourTakesItsCheckWithIt() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        XCTAssertNotNil(store.dropHour(subjectId: "upwork", instanceId: slot.instanceId))

        let window = try XCTUnwrap(store.windowFor(subjectId: "upwork"))
        XCTAssertEqual(window.hours, [ClockTime(hour: 10, minute: 0), ClockTime(hour: 15, minute: 0)])
        XCTAssertEqual(store.subject(id: "upwork")?.cadence.count, 2)
        XCTAssertEqual(occurrences(store).count, 2)
        XCTAssertNil(store.snapshot.instances.first { $0.id == slot.instanceId })
        XCTAssertNil(store.snapshot.widgets.first { $0.id == slot.widgetId })
        XCTAssertFalse(try XCTUnwrap(store.subject(id: "upwork")).instanceIds.contains(slot.instanceId))
        assertHoursMatchOccurrences(store)
    }

    func testDroppingAnHourTakesItsAlarmDown() throws {
        let store = try makeUpwork()
        let slot = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        store.dropHour(subjectId: "upwork", instanceId: slot.instanceId)
        XCTAssertEqual(alarmHours(store), [ClockTime(hour: 10, minute: 0), ClockTime(hour: 15, minute: 0)])
    }

    /// A window with no hour cannot fire and cannot be drawn — `hours_required`
    /// in the law. The carousel never offers it, and the store refuses it.
    func testTheLastHourCannotGo() throws {
        let store = try makeUpwork()
        var left = try XCTUnwrap(store.hourGroup(subjectId: "upwork")).marks
        while left.count > 1 {
            let slot = try XCTUnwrap(store.hourSlot(subjectId: "upwork", instanceId: left[0].instanceId))
            XCTAssertTrue(slot.canDrop)
            store.dropHour(subjectId: "upwork", instanceId: slot.instanceId)
            left = store.hourGroup(subjectId: "upwork")?.marks ?? []
        }
        // One hour left: not a group any more, so there is nothing to drop and
        // no `1/1` tile either.
        XCTAssertNil(store.hourGroup(subjectId: "upwork"))
        XCTAssertEqual(try XCTUnwrap(store.windowFor(subjectId: "upwork")).hours.count, 1)
        XCTAssertEqual(occurrences(store).count, 1)
        XCTAssertTrue(store.snapshot.widgets.filter { $0.subjectId == "upwork" }.allSatisfy { $0.groupId == nil })
        assertHoursMatchOccurrences(store)
    }

    // MARK: - a closed check is history

    func testAClosedCheckIsNotMovedAndNotDropped() throws {
        let store = try makeUpwork()
        let noon = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        store.closeOccurrence(widgetId: noon.widgetId)

        let closed = try XCTUnwrap(store.hourSlot(subjectId: "upwork", instanceId: noon.instanceId))
        XCTAssertTrue(closed.closed)
        XCTAssertFalse(closed.canMove)
        XCTAssertFalse(closed.canDrop)

        let before = store.snapshot
        XCTAssertFalse(store.moveHour(subjectId: "upwork", instanceId: noon.instanceId, to: ClockTime(hour: 13, minute: 0)))
        XCTAssertNil(store.dropHour(subjectId: "upwork", instanceId: noon.instanceId))
        XCTAssertEqual(store.snapshot, before)
        assertHoursMatchOccurrences(store)
    }

    /// Editing around a closed check must not repaint its hour: the mark that
    /// was ticked at 12:00 stays the 12:00 mark (R16 `closingStamp`).
    func testEditingAroundAClosedCheckLeavesItsHourAlone() throws {
        let store = try makeUpwork()
        let noon = try XCTUnwrap(slot(store, at: ClockTime(hour: 12, minute: 0)))
        store.closeOccurrence(widgetId: noon.widgetId)
        store.addHour(subjectId: "upwork", clock: ClockTime(hour: 8, minute: 0))

        let still = try XCTUnwrap(store.snapshot.instances.first { $0.id == noon.instanceId })
        XCTAssertEqual(ReminderClock.clock(from: still.when), ClockTime(hour: 12, minute: 0))
        XCTAssertEqual(occurrences(store).count, 4)
        assertHoursMatchOccurrences(store)
    }

    // MARK: - the whole run, in one go

    func testAddMoveAndDropAllLeaveTheTwoNumbersEqual() throws {
        let store = try makeUpwork()
        assertHoursMatchOccurrences(store)

        let added = try XCTUnwrap(store.addHour(subjectId: "upwork", clock: ClockTime(hour: 19, minute: 30)))
        assertHoursMatchOccurrences(store)

        XCTAssertTrue(store.moveHour(subjectId: "upwork", instanceId: added, to: ClockTime(hour: 20, minute: 0)))
        assertHoursMatchOccurrences(store)

        XCTAssertNotNil(store.dropHour(subjectId: "upwork", instanceId: added))
        assertHoursMatchOccurrences(store)

        XCTAssertEqual(occurrenceHours(store), hours)
        XCTAssertEqual(store.subject(id: "upwork")?.cadence.count, 3)
    }

    func testTheEditsSurviveARelaunch() throws {
        let (store, repository) = try makeUpworkDesk()
        store.addHour(subjectId: "upwork", clock: ClockTime(hour: 19, minute: 30))
        let reopened = try DeskStore(repository: repository, now: { self.stamp })
        XCTAssertEqual(try XCTUnwrap(reopened.windowFor(subjectId: "upwork")).hours.count, 4)
        XCTAssertEqual(occurrences(reopened).count, 4)
        assertHoursMatchOccurrences(reopened)
    }


    // MARK: - helpers

    /// The whole point, asserted after every operation: as many stated hours as
    /// there are checks, and the group saying each of them.
    private func assertHoursMatchOccurrences(
        _ store: DeskStore,
        file: StaticString = #filePath,
        line: UInt = #line
    ) {
        guard let window = store.windowFor(subjectId: "upwork") else {
            return XCTFail("upwork lost its window", file: file, line: line)
        }
        let cases = occurrences(store)
        XCTAssertEqual(
            window.hours.count,
            cases.count,
            "\(window.hours.count) stated hours against \(cases.count) checks",
            file: file,
            line: line
        )
        XCTAssertEqual(occurrenceHours(store), window.hours, "a check is not on its hour", file: file, line: line)
        // Every check has a widget of its own, and no widget lost its case.
        let widgets = store.snapshot.widgets.filter { $0.subjectId == "upwork" && $0.type == .tick }
        XCTAssertEqual(widgets.count, cases.count, "checks and tiles disagree", file: file, line: line)
        XCTAssertEqual(Set(widgets.map(\.instanceId)), Set(cases.map(\.id)), file: file, line: line)
        guard window.hours.count > 1 else { return }
        let face = GroupLaw.face(
            of: GroupLaw.key(subjectId: "upwork", day: stamp),
            widgets: store.snapshot.widgets,
            instances: store.snapshot.instances,
            now: stamp
        )
        guard let face else { return XCTFail("the group stopped drawing", file: file, line: line) }
        XCTAssertEqual(face.total, cases.count, file: file, line: line)
        XCTAssertTrue(
            GroupLaw.saysEveryHour(face, window: window),
            "the group stopped saying every hour — R17 would give the reminder tile back",
            file: file,
            line: line
        )
    }

    private func occurrences(_ store: DeskStore) -> [Instance] {
        let alarms = SlotLaw.hourInstanceIds(subjectId: "upwork", widgets: store.snapshot.widgets)
        return store.snapshot.instances
            .filter { $0.subjectId == "upwork" && SlotLaw.isSameDay($0.when, stamp) && !alarms.contains($0.id) }
            .sorted { $0.when < $1.when }
    }

    private func occurrenceHours(_ store: DeskStore) -> [ClockTime] {
        occurrences(store).map { ReminderClock.clock(from: $0.when) }.sorted()
    }

    /// The hours this practice rings on **today**. Since R20 the scheduler also
    /// lays the same window on the next days of its horizon, and these tests
    /// are about the window, not about how far ahead it reaches.
    private func alarmHours(_ store: DeskStore) -> [ClockTime] {
        ReminderScheduler.alarms(from: store.snapshot, now: stamp)
            .filter { $0.id.contains("upwork") && SlotLaw.isSameDay($0.fireAt, stamp) }
            .map { ReminderClock.clock(from: $0.fireAt) }
            .sorted()
    }

    private func slot(_ store: DeskStore, at hour: ClockTime) -> OccurrenceHourLaw.HourSlot? {
        guard let mark = store.hourGroup(subjectId: "upwork")?.marks.first(where: { $0.hour == hour }) else {
            return nil
        }
        return store.hourSlot(subjectId: "upwork", instanceId: mark.instanceId)
    }

    private var stamp: Date {
        FacioJSON.date(from: "2026-08-30T07:00:00") ?? Date()
    }

    private var hours: [ClockTime] {
        [10, 12, 15].map { ClockTime(hour: $0, minute: 0) }
    }

    private func makeUpwork() throws -> DeskStore {
        try makeUpworkDesk().0
    }

    /// Three checks a day at three stated hours, with the alarm that rings
    /// them. The reminder tile is hidden from the lid by R17 — which is what
    /// makes the carousel the only place these hours can be corrected.
    private func makeUpworkDesk() throws -> (DeskStore, DeskRepository) {
        let now = stamp
        var snapshot = try SeedFactory.buildSeed(now: now)
        let window = TimeWindow(hours: hours)
        snapshot.subjects.append(
            Subject(
                id: "upwork",
                title: "проверить upwork",
                cadence: try Cadence.of(count: 3, period: .day),
                window: window,
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
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
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
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-hours-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(snapshot)
        return (try DeskStore(repository: repository, now: { now }), repository)
    }
}
