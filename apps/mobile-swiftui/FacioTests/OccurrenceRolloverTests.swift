import XCTest
@testable import Facio

/// R19: the day rolls over.
///
/// R16 gave the occurrences of one day a `group_id` and one tile; R18 measured
/// that the whole construction lived exactly one day — the top-up needed a
/// widget bound to a case of *that* date, and a fresh day has none, so tomorrow
/// wrote zero checks and the card simply did not come back.
///
/// Everything here runs on a **substituted `now`**, never a wait: a store is
/// reopened on the next date, which is exactly what `DeskStore.init` and the
/// foreground return do on a real phone. Two days in a row on purpose — a
/// rollover that happens once is not a rhythm.
@MainActor
final class OccurrenceRolloverTests: XCTestCase {
    // MARK: - the day rolls over

    func testTomorrowGetsAsManyChecksAsTheRhythmPromises() throws {
        let (_, repository) = try makeUpworkDesk()
        let second = try DeskStore(repository: repository, now: { self.day(1) })

        let ticks = todayTicks(second, subjectId: "upwork")
        XCTAssertEqual(ticks.count, 7)
        XCTAssertEqual(Set(ticks.map(\.instanceId)).count, 7)
        XCTAssertTrue(ticks.allSatisfy { $0.status == .ready })
        // The face carried over, the state did not.
        XCTAssertTrue(ticks.allSatisfy { $0.payload.done != true })
        XCTAssertTrue(ticks.allSatisfy { $0.title == "проверить upwork" })
    }

    func testTomorrowsChecksWearTheWindowsHours() throws {
        let (_, repository) = try makeUpworkDesk()
        let second = try DeskStore(repository: repository, now: { self.day(1) })

        let hours = try XCTUnwrap(second.windowFor(subjectId: "upwork")).hours
        let worn = todayCases(second, subjectId: "upwork")
            .map { ReminderClock.clock(from: $0.when) }
            .sorted()
        XCTAssertEqual(worn, hours)
        XCTAssertTrue(todayCases(second, subjectId: "upwork").allSatisfy {
            SlotLaw.isSameDay($0.when, self.day(1))
        })
    }

    func testTheRolloverIsNotAOneOff() throws {
        let (_, repository) = try makeUpworkDesk()
        _ = try DeskStore(repository: repository, now: { self.day(1) })
        let third = try DeskStore(repository: repository, now: { self.day(2) })

        XCTAssertEqual(todayTicks(third, subjectId: "upwork").count, 7)
        XCTAssertEqual(todayCases(third, subjectId: "upwork").count, 7)
        // Three days of checks stand on the desk, one day each, none merged.
        for offset in 0...2 {
            let onThatDay = third.snapshot.instances.filter {
                $0.subjectId == "upwork" && SlotLaw.isSameDay($0.when, self.day(offset))
            }
            XCTAssertEqual(onThatDay.count, 7, "day \(offset)")
        }
        XCTAssertEqual(third.snapshot.instances.filter { $0.subjectId == "upwork" }.count, 21)
    }

    func testTheTopUpIsStillIdempotentOnTheNewDay() throws {
        let (_, repository) = try makeUpworkDesk()
        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let before = second.snapshot
        second.ensureOccurrences()
        second.ensureOccurrences()
        XCTAssertEqual(second.snapshot, before)
    }

    // MARK: - a new day is a new group

    func testTheNewDayGetsItsOwnGroupId() throws {
        let (_, repository) = try makeUpworkDesk()
        let second = try DeskStore(repository: repository, now: { self.day(1) })

        let today = GroupLaw.key(subjectId: "upwork", day: day(1))
        let yesterday = GroupLaw.key(subjectId: "upwork", day: day(0))
        XCTAssertNotEqual(today, yesterday)
        XCTAssertEqual(Set(todayTicks(second, subjectId: "upwork").compactMap(\.groupId)), [today])
        // Yesterday's checks keep yesterday's id — the lid must not glue two
        // days into one tile.
        let old = second.snapshot.widgets.filter { $0.groupId == yesterday }
        XCTAssertEqual(old.count, 7)
    }

    func testTheLidDrawsOneGroupTileForTheDayAndNotTwo() throws {
        let (_, repository) = try makeUpworkDesk()
        let second = try DeskStore(repository: repository, now: { self.day(1) })

        let widgets = todayWidgets(second)
        let cells = GroupLaw.cells(widgets, instances: second.snapshot.instances, now: day(1))
        let groups: [GroupFace] = cells.compactMap {
            if case .group(let face) = $0 { return face } else { return nil }
        }
        XCTAssertEqual(groups.count, 1)
        XCTAssertEqual(groups.first?.id, GroupLaw.key(subjectId: "upwork", day: day(1)))
        XCTAssertEqual(groups.first?.total, 7)
        XCTAssertEqual(groups.first?.done, 0)
        XCTAssertEqual(groups.first?.nextHour, ClockTime(hour: 10, minute: 0))
        // Not one widget of yesterday's group is drawn on the new day.
        let yesterday = GroupLaw.key(subjectId: "upwork", day: day(0))
        XCTAssertFalse(widgets.contains { $0.groupId == yesterday })
    }

    // MARK: - yesterday stays yesterday

    func testYesterdaysMissesAreNotCarriedAndNotRewritten() throws {
        let (first, repository) = try makeUpworkDesk()
        let marks = try face(first, on: day(0)).marks
        first.closeOccurrence(widgetId: marks[0].widgetId)
        first.closeOccurrence(widgetId: marks[2].widgetId)
        let closedIds = [marks[0].widgetId, marks[2].widgetId]

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let old = second.snapshot.widgets.filter {
            $0.groupId == GroupLaw.key(subjectId: "upwork", day: self.day(0))
        }
        XCTAssertEqual(old.count, 7)
        // Nothing moved to today, nothing was resurrected, nothing was closed
        // for the person: two done, five still open and still missed.
        XCTAssertEqual(Set(old.filter { $0.status == .done }.map(\.id)), Set(closedIds))
        XCTAssertEqual(old.filter { $0.status == .ready }.count, 5)
        let oldCases = second.snapshot.instances.filter { instance in
            old.contains { $0.instanceId == instance.id }
        }
        XCTAssertEqual(oldCases.count, 7)
        XCTAssertTrue(oldCases.allSatisfy { SlotLaw.isSameDay($0.when, self.day(0)) })
        XCTAssertEqual(oldCases.filter { $0.status == .completed }.count, 2)
        XCTAssertEqual(oldCases.filter { $0.status == .prepared }.count, 5)
        // And today starts empty: a miss is a miss, not a debt handed forward.
        XCTAssertEqual(try face(second, on: day(1)).done, 0)
    }

    func testYesterdaysMissesStillCountForTheDelta() throws {
        let (first, repository) = try makeUpworkDesk()
        let marks = try face(first, on: day(0)).marks
        first.closeOccurrence(widgetId: marks[0].widgetId)

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let upwork = try XCTUnwrap(second.subject(id: "upwork"))
        // A daily rhythm's period is one day, so yesterday's single close is
        // not today's credit: the day owes seven again.
        XCTAssertEqual(
            MorningLaw.delta(upwork, instances: second.snapshot.instances, now: day(1)),
            7
        )
        // Yesterday still reads as one done out of seven where it happened.
        XCTAssertEqual(
            MorningLaw.doneInPeriod(upwork, instances: second.snapshot.instances, now: day(0)),
            1
        )
    }

    // MARK: - the alarms of the new day

    /// R19 asserted seven alarms on the new day, put there by rolling the
    /// widget's stamp forward. R20 removed the roll — the day now comes from
    /// the rhythm, which reaches `horizonDays` ahead — so the seven are still
    /// there on the new day, and the days after it carry their own seven.
    func testTheAlarmsStandOnTheNewDaysHours() throws {
        let (first, repository) = try makeUpworkDesk(withReminder: true)
        XCTAssertEqual(alarms(first, on: day(0)).count, 7)

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let today = alarms(second, on: day(1))
        XCTAssertEqual(today.count, 7)
        XCTAssertEqual(
            today.map { ReminderClock.clock(from: $0.fireAt) }.sorted(),
            try XCTUnwrap(second.windowFor(subjectId: "upwork")).hours
        )
        // Yesterday's alarms are behind us; the scheduler drops what has passed.
        XCTAssertTrue(today.allSatisfy { $0.fireAt > self.day(1) })

        // A daily practice is owed something every day, so the horizon rings on
        // every one of its days — and never twice on the same hour of the same
        // day, or the notification centre would drop the duplicate.
        let all = ReminderScheduler.alarms(from: second.snapshot, now: day(1))
            .filter { $0.id.contains("upwork") }
        XCTAssertEqual(all.count, 7 * ReminderScheduler.horizonDays)
        XCTAssertEqual(Set(all.map(\.id)).count, all.count)
        XCTAssertTrue(all.allSatisfy { $0.fireAt > self.day(1) })
    }

    /// The stamp on the reminder widget is not moved by anyone any more (R20):
    /// it is a mark of the next fire, and the ringing no longer depends on it.
    func testTheAlarmsRingWithoutTheStampBeingRewritten() throws {
        let (first, repository) = try makeUpworkDesk(withReminder: true)
        let stamp = first.widget(id: "upwork-reminder")?.reminderFireAt
        let third = try DeskStore(repository: repository, now: { self.day(2) })
        XCTAssertEqual(third.widget(id: "upwork-reminder")?.reminderFireAt, stamp)
        XCTAssertEqual(alarms(third, on: day(2)).count, 7)
    }

    private func alarms(_ store: DeskStore, on when: Date) -> [ReminderAlarm] {
        ReminderScheduler.alarms(from: store.snapshot, now: when)
            .filter { $0.id.contains("upwork") && SlotLaw.isSameDay($0.fireAt, when) }
    }

    func testTheReminderTileStaysHiddenBehindTheNewDaysGroup() throws {
        let (_, repository) = try makeUpworkDesk(withReminder: true)
        let second = try DeskStore(repository: repository, now: { self.day(1) })
        // R17: one practice, one card. The group of the new day says every
        // hour, so the reminder is not drawn — and is not deleted either.
        XCTAssertFalse(todayWidgets(second).contains { $0.type == .reminder && $0.subjectId == "upwork" })
        XCTAssertEqual(
            second.snapshot.widgets.filter { $0.subjectId == "upwork" && $0.type == .reminder }.count,
            1
        )
    }

    // MARK: - a practice without a group is untouched

    /// Contract 6. The group's rollover must not reach a practice that has no
    /// group: the daily tick comes back by having its one tile **rebound**
    /// (S5), and the weekly ride is not day-counted at all.
    func testAPracticeWithoutAGroupIsNotMultipliedByTheGroupRollover() throws {
        let (first, repository) = try makeUpworkDesk(withReminder: true)
        let before = ungrouped(first.snapshot)

        for offset in [1, 2] {
            let later = try DeskStore(repository: repository, now: { self.day(offset) })
            let now = ungrouped(later.snapshot)
            // One widget each, on every day, and none of them acquires a group.
            XCTAssertEqual(now.widgets.map(\.id), before.widgets.map(\.id), "day \(offset)")
            XCTAssertTrue(now.widgets.allSatisfy { $0.groupId == nil }, "day \(offset)")
            // The weekly promises are untouched, cases included (Q26).
            for id in ["push-ups", "bike"] {
                XCTAssertEqual(
                    now.instances.filter { $0.subjectId == id },
                    before.instances.filter { $0.subjectId == id },
                    "\(id) on day \(offset)"
                )
            }
        }
    }

    func testADailyTickIsStillOneWidgetOnTheThirdDay() throws {
        let (_, repository) = try makeUpworkDesk()
        _ = try DeskStore(repository: repository, now: { self.day(1) })
        let third = try DeskStore(repository: repository, now: { self.day(2) })

        let veg = third.snapshot.widgets.filter { $0.subjectId == "vegetables" }
        XCTAssertEqual(veg.count, 1)
        XCTAssertNil(veg.first?.groupId)
        // One tile, but one case per day it stood over: two of them never
        // happened and stay `prepared` on their own day (S5).
        let cases = third.snapshot.instances.filter { $0.subjectId == "vegetables" }
        XCTAssertEqual(cases.count, 3)
        XCTAssertTrue(cases.allSatisfy { $0.status == .prepared })
        XCTAssertEqual(Set(cases.map { SlotLaw.dayKey($0.when) }).count, 3)
        // The weekly ones are not day-counted at all.
        XCTAssertEqual(third.snapshot.instances.filter { $0.subjectId == "push-ups" }.count, 1)
        XCTAssertEqual(third.snapshot.widgets.filter { $0.subjectId == "bike" }.count, 1)
    }

    /// A desk written before Q34 has no `group_id` anywhere and never grows
    /// one: it opens on any later day with the same widgets it always had, and
    /// nothing about it becomes a group.
    func testAnOldDeskWithoutGroupsGrowsNoGroupOnALaterDay() throws {
        let now = day(0)
        var snapshot = try SeedFactory.buildSeed(now: now)
        snapshot.widgets = snapshot.widgets.map { widget in
            var next = widget
            next.groupId = nil
            return next
        }
        let repository = try makeRepository()
        try repository.saveSnapshot(snapshot)
        let opened = try DeskStore(repository: repository, now: { now })
        let later = try DeskStore(repository: repository, now: { self.day(3) })
        XCTAssertTrue(later.snapshot.widgets.allSatisfy { $0.groupId == nil })
        XCTAssertEqual(later.snapshot.widgets.map(\.id).sorted(), opened.snapshot.widgets.map(\.id).sorted())
        XCTAssertEqual(later.snapshot.subjects.map(\.id).sorted(), opened.snapshot.subjects.map(\.id).sorted())
        // Only the daily practice's tile follows the day (S5); the weekly ones
        // keep the single case they opened with.
        for id in ["push-ups", "bike"] {
            XCTAssertEqual(
                later.snapshot.instances.filter { $0.subjectId == id },
                opened.snapshot.instances.filter { $0.subjectId == id },
                id
            )
        }
    }

    // MARK: - a day that closed owes the next one (R19's other half)

    /// Measured on the founding seed, three days running: vegetables is
    /// `1×/day`, it was ticked on day 0, and on day 1 the lid had **no tile
    /// for it at all** — and no line either, because the delta is one card and
    /// push-ups won it. On day 3 the same practice produced a **drift card**:
    /// the product accusing the person of silence about a practice it had
    /// taken off Today itself.
    ///
    /// `SlotLaw` projects the due slot for tomorrow all along; it was the hand
    /// that writes the case that refused, because R19 limited the roll-forward
    /// to a practice promising more than one a day.
    func testADailyPracticeClosedYesterdayIsBackOnTheLidToday() throws {
        let repository = try makeSeedRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        first.toggleTick(widgetId: "vegetables-tick")

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let tiles = todayWidgets(second).filter { $0.subjectId == "vegetables" }
        XCTAssertEqual(tiles.count, 1)
        XCTAssertEqual(tiles.first?.status, .ready)
        XCTAssertEqual(tiles.first?.payload.done, false)
        let standing = try XCTUnwrap(
            second.snapshot.instances.first { $0.id == tiles.first?.instanceId }
        )
        XCTAssertTrue(SlotLaw.isSameDay(standing.when, day(1)))
    }

    /// The roll rebinds the standing tile; it never copies it. One practice,
    /// one tile (R17) — and an old desk does not grow a widget a day.
    func testTheDailyRollIsOneTileAndOneCasePerDay() throws {
        let repository = try makeSeedRepository()
        for offset in 0...2 {
            let store = try DeskStore(repository: repository, now: { self.day(offset) })
            store.toggleTick(widgetId: "vegetables-tick")
        }
        let fourth = try DeskStore(repository: repository, now: { self.day(3) })
        XCTAssertEqual(fourth.snapshot.widgets.filter { $0.subjectId == "vegetables" }.count, 1)
        for offset in 0...2 {
            let onThatDay = fourth.snapshot.instances.filter {
                $0.subjectId == "vegetables" && SlotLaw.isSameDay($0.when, self.day(offset))
            }
            XCTAssertEqual(onThatDay.count, 1, "day \(offset)")
            XCTAssertEqual(onThatDay.first?.status, .completed, "day \(offset)")
        }
    }

    /// Yesterday is not rewritten — the same line R19 took. A closed day keeps
    /// its date and its status, so the delta and the drift go on counting it.
    func testTheDailyRollLeavesYesterdayAlone() throws {
        let repository = try makeSeedRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        first.toggleTick(widgetId: "vegetables-tick")
        let closed = try XCTUnwrap(
            first.snapshot.instances.first { $0.subjectId == "vegetables" && $0.status == .completed }
        )

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let sameCase = try XCTUnwrap(second.snapshot.instances.first { $0.id == closed.id })
        XCTAssertEqual(sameCase, closed)
        XCTAssertEqual(MorningLaw.doneInPeriod(
            try XCTUnwrap(second.subject(id: "vegetables")),
            instances: second.snapshot.instances,
            now: day(0)
        ), 1)
    }

    // MARK: - yesterday's miss is not erased (S5)

    /// This test used to assert the opposite — «a desk nobody touched opens
    /// byte-identical on a later day» — and that sentence was the bug. An
    /// untouched daily tile is `ready` on Today for ever, so R19 read it as
    /// «already asking today» and never rebound it; the case underneath went on
    /// standing on the day it was written for.
    func testAnUntouchedDailyTileAsksAboutTodayAndNotAboutYesterday() throws {
        let repository = try makeSeedRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        let yesterdaysCase = try XCTUnwrap(
            first.snapshot.instances.first { $0.subjectId == "vegetables" }
        )

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let tiles = second.snapshot.widgets.filter { $0.subjectId == "vegetables" }
        XCTAssertEqual(tiles.count, 1, "one practice, one tile — rebound, never copied")
        let tile = try XCTUnwrap(tiles.first)
        XCTAssertEqual(tile.status, .ready)
        XCTAssertNotEqual(tile.instanceId, yesterdaysCase.id)
        let standing = try XCTUnwrap(second.snapshot.instances.first { $0.id == tile.instanceId })
        XCTAssertTrue(SlotLaw.isSameDay(standing.when, day(1)))

        // Yesterday keeps its own case, exactly as yesterday left it: promised,
        // never closed. That is what a miss looks like on this desk (R19).
        let stale = try XCTUnwrap(second.snapshot.instances.first { $0.id == yesterdaysCase.id })
        XCTAssertEqual(stale, yesterdaysCase)
        XCTAssertEqual(stale.status, .prepared)
    }

    /// The whole point, in the shape the PO named it: ticking the tile today
    /// must not reach back and stamp yesterday's promise with «now».
    func testTickingTodayDoesNotEraseYesterdaysMiss() throws {
        let repository = try makeSeedRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        let missed = try XCTUnwrap(first.snapshot.instances.first { $0.subjectId == "vegetables" })

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        second.toggleTick(widgetId: "vegetables-tick")

        let cases = second.snapshot.instances.filter { $0.subjectId == "vegetables" }
        XCTAssertEqual(cases.count, 2)
        let stillMissed = try XCTUnwrap(cases.first { $0.id == missed.id })
        XCTAssertEqual(stillMissed.status, .prepared)
        XCTAssertTrue(SlotLaw.isSameDay(stillMissed.when, day(0)))
        let closed = try XCTUnwrap(cases.first { $0.id != missed.id })
        XCTAssertEqual(closed.status, .completed)
        XCTAssertTrue(SlotLaw.isSameDay(closed.when, day(1)))

        // Two days, two promises, one close. The arithmetic has to say so on
        // both days — before S5 day 0 read as one done out of one.
        let veg = try XCTUnwrap(second.subject(id: "vegetables"))
        XCTAssertEqual(MorningLaw.doneInPeriod(veg, instances: second.snapshot.instances, now: day(0)), 0)
        XCTAssertEqual(MorningLaw.doneInPeriod(veg, instances: second.snapshot.instances, now: day(1)), 1)
    }

    /// A set in progress is not rolled. Crossing midnight mid-run would reset
    /// the payload and throw away a count the person is holding (P6), and the
    /// run is itself the ask.
    func testALiveRunIsNotRolledAcrossMidnight() throws {
        let repository = try makeDailyCounterRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        first.tickCounter(widgetId: "squats-counter", delta: 1)
        let running = try XCTUnwrap(first.widget(id: "squats-counter"))
        XCTAssertEqual(running.status, .running)

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        let still = try XCTUnwrap(second.widget(id: "squats-counter"))
        XCTAssertEqual(still.instanceId, running.instanceId)
        XCTAssertEqual(still.payload.count, running.payload.count)
        XCTAssertEqual(second.snapshot.instances.filter { $0.subjectId == "squats" }.count, 1)
    }

    /// Postponed was said out loud and may carry a day of its own, so the roll
    /// leaves it alone — the same line R19 took.
    func testAPostponedTileIsNotRolled() throws {
        let repository = try makeSeedRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        XCTAssertTrue(first.postpone(subjectId: "vegetables"))
        let before = first.snapshot.instances.filter { $0.subjectId == "vegetables" }

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        XCTAssertEqual(second.snapshot.instances.filter { $0.subjectId == "vegetables" }, before)
        XCTAssertEqual(second.widget(id: "vegetables-tick")?.status, .snoozed)
    }

    /// A daily counter of its own, because the founding seed's daily practice
    /// is a tick and a tick has no running state to leave open.
    private func makeDailyCounterRepository() throws -> DeskRepository {
        let now = day(0)
        var snapshot = try SeedFactory.buildSeed(now: now)
        snapshot.subjects.append(
            Subject(
                id: "squats",
                title: "приседания",
                cadence: try Cadence.of(count: 1, period: .day),
                instanceIds: ["squats-open"]
            )
        )
        snapshot.instances.append(
            Instance(id: "squats-open", subjectId: "squats", when: now, status: .prepared)
        )
        snapshot.widgets.append(
            Widget(
                id: "squats-counter",
                type: .counter,
                title: "приседания",
                payload: WidgetPayload(count: 0, target: 20),
                status: .ready,
                section: .today,
                subjectId: "squats",
                instanceId: "squats-open",
                tileSize: .compact
            )
        )
        let repository = try makeRepository()
        try repository.saveSnapshot(snapshot)
        return repository
    }

    /// Only a promise counted **per day** rolls. A weekly one is silent here on
    /// purpose: which day of the week its tile lands on is not decided (Q26),
    /// and guessing it would be the law inventing a weekday.
    func testAWeeklyPracticeIsNotRolledByThisRule() throws {
        let repository = try makeSeedRepository()
        let first = try DeskStore(repository: repository, now: { self.day(0) })
        first.completeCounter(widgetId: "push-ups-counter")
        let before = first.snapshot.instances.filter { $0.subjectId == "push-ups" }

        let second = try DeskStore(repository: repository, now: { self.day(1) })
        XCTAssertEqual(second.snapshot.instances.filter { $0.subjectId == "push-ups" }, before)
    }

    private func makeSeedRepository() throws -> DeskRepository {
        let repository = try makeRepository()
        try repository.saveSnapshot(try SeedFactory.buildSeed(now: day(0)))
        return repository
    }

    // MARK: -

    private func day(_ offset: Int) -> Date {
        let start = FacioJSON.date(from: "2026-08-30T09:00:00") ?? Date()
        return SlotLaw.dayCalendar.date(byAdding: .day, value: offset, to: start) ?? start
    }

    private func face(_ store: DeskStore, on when: Date) throws -> GroupFace {
        try XCTUnwrap(
            GroupLaw.face(
                of: GroupLaw.key(subjectId: "upwork", day: when),
                widgets: store.snapshot.widgets,
                instances: store.snapshot.instances,
                now: when
            )
        )
    }

    private func todayWidgets(_ store: DeskStore) -> [Widget] {
        store.lid.today.compactMap { item in
            if case .widget(_, let widget) = item { return widget }
            return nil
        }
    }

    private func todayTicks(_ store: DeskStore, subjectId: String) -> [Widget] {
        todayWidgets(store).filter { $0.subjectId == subjectId && $0.type == .tick }
    }

    private func todayCases(_ store: DeskStore, subjectId: String) -> [Instance] {
        let ids = Set(todayTicks(store, subjectId: subjectId).map(\.instanceId))
        return store.snapshot.instances.filter { ids.contains($0.id) }
    }

    private struct Ungrouped: Equatable {
        var widgets: [Widget]
        var instances: [Instance]
    }

    /// Everything on the desk that never belonged to a group, in a stable order.
    private func ungrouped(_ snapshot: DeskSnapshot) -> Ungrouped {
        Ungrouped(
            widgets: snapshot.widgets
                .filter { $0.subjectId != "upwork" }
                .sorted { $0.id < $1.id },
            instances: snapshot.instances
                .filter { $0.subjectId != "upwork" }
                .sorted { $0.id < $1.id }
        )
    }

    private func makeRepository() throws -> DeskRepository {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-rollover-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return DeskRepository(directory: directory)
    }

    private func makeUpworkDesk(withReminder: Bool = false) throws -> (DeskStore, DeskRepository) {
        let now = day(0)
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
            let fireAt = ReminderClock.reminderFireAt(window: TimeWindow(hours: hours), on: now)
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
        let repository = try makeRepository()
        try repository.saveSnapshot(snapshot)
        return (try DeskStore(repository: repository, now: { now }), repository)
    }
}
