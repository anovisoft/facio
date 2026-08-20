import XCTest
@testable import Facio

final class SlotLawTests: XCTestCase {
    func testHorizonIsSevenConsecutiveDaysFromOrigin() throws {
        let now = try DomainFixtures.now()
        let origin = SlotLaw.startOfDay(for: now)
        let desk = try SeedFactory.buildSeed(now: now)
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let dates = horizon.days.map(\.date)
        XCTAssertEqual(dates.count, 7)
        XCTAssertEqual(SlotLaw.dayKey(dates[0]), SlotLaw.dayKey(origin))
        let calendar = SlotLaw.dayCalendar
        let expected = (0..<7).compactMap { calendar.date(byAdding: .day, value: $0, to: origin) }
        XCTAssertEqual(dates.map(SlotLaw.dayKey), expected.map(SlotLaw.dayKey))
    }

    func testFoundingVegetablesTodayRealThenProjectedDue() throws {
        let now = try DomainFixtures.now()
        let origin = SlotLaw.startOfDay(for: now)
        let desk = try SeedFactory.buildSeed(now: now)
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let vegetables = slots(horizon, subjectId: "vegetables")
        let today = vegetables.filter { SlotLaw.isSameDay($0.date, origin) }
        XCTAssertEqual(today.count, 1)
        XCTAssertEqual(today[0].kind, .due)
        XCTAssertEqual(today[0].instanceId, "vegetables-open")
        let laterDays = vegetables.filter { $0.date > origin }
        let calendar = SlotLaw.dayCalendar
        let expected = (1..<7).compactMap { calendar.date(byAdding: .day, value: $0, to: origin) }
        XCTAssertEqual(laterDays.map { SlotLaw.dayKey($0.date) }, expected.map(SlotLaw.dayKey))
        XCTAssertTrue(laterDays.allSatisfy { $0.kind == .due })
        XCTAssertTrue(laterDays.allSatisfy { $0.instanceId == nil })
    }

    func testFoundingPushUpsDoNotMarkWeekdaysBeforeOriginMissed() throws {
        let now = try DomainFixtures.now()
        let origin = SlotLaw.startOfDay(for: now)
        let desk = try SeedFactory.buildSeed(now: now)
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let dayKeys = Set(horizon.days.map { SlotLaw.dayKey($0.date) })
        XCTAssertFalse(dayKeys.contains("2026-08-10"))
        XCTAssertFalse(dayKeys.contains("2026-08-11"))
        let today = slots(horizon, subjectId: "push-ups").filter { SlotLaw.isSameDay($0.date, origin) }
        XCTAssertTrue(today.contains { $0.instanceId == "push-ups-open" && $0.kind == .due })
    }

    func testWeeklyProjectionsFillRemainingDaysNotPastMondayTuesday() throws {
        let origin = SlotLaw.startOfDay(for: noon(2026, 8, 12))
        let desk = try desk([subject("push-ups", cadence: Cadence.of(count: 3, period: .week))])
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let projected = slots(horizon, subjectId: "push-ups")
        let thisSunday = SlotLaw.startOfDay(for: noon(2026, 8, 16))
        let thisWeek = projected.map(\.date).filter { $0 <= thisSunday }
        XCTAssertEqual(thisWeek.map(SlotLaw.dayKey), ["2026-08-12", "2026-08-13", "2026-08-14"])
        XCTAssertTrue(projected.allSatisfy { $0.instanceId == nil })
        let dayKeys = Set(horizon.days.map { SlotLaw.dayKey($0.date) })
        XCTAssertFalse(dayKeys.contains("2026-08-10"))
        XCTAssertFalse(dayKeys.contains("2026-08-11"))
        let projectedKeys = Set(projected.map { SlotLaw.dayKey($0.date) })
        XCTAssertFalse(projectedKeys.contains("2026-08-10"))
        XCTAssertFalse(projectedKeys.contains("2026-08-11"))
    }

    func testWeeklyLeftoverDoesNotSpillIntoNextWeek() throws {
        let origin = SlotLaw.startOfDay(for: noon(2026, 8, 15))
        let desk = try desk([subject("push-ups", cadence: Cadence.of(count: 3, period: .week))])
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let projected = slots(horizon, subjectId: "push-ups").map { SlotLaw.dayKey($0.date) }
        XCTAssertTrue(projected.contains("2026-08-15"))
        XCTAssertTrue(projected.contains("2026-08-16"))
        XCTAssertEqual(projected, ["2026-08-15", "2026-08-16", "2026-08-17", "2026-08-18", "2026-08-19"])
        XCTAssertFalse(projected.contains("2026-08-20"))
    }

    func testCompletedBeforeOriginIsNeitherInDaysNorLater() throws {
        let origin = SlotLaw.startOfDay(for: noon(2026, 8, 12))
        let tuesday = noon(2026, 8, 11)
        let desk = try desk(
            [subject("push-ups", cadence: Cadence.of(count: 3, period: .week))],
            [Instance(id: "done-tue", subjectId: "push-ups", when: tuesday, status: .completed)]
        )
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let dayKeys = Set(horizon.days.map { SlotLaw.dayKey($0.date) })
        XCTAssertFalse(dayKeys.contains("2026-08-11"))
        XCTAssertFalse(horizon.later.contains { SlotLaw.dayKey($0) == "2026-08-11" })
        XCTAssertTrue(slots(horizon, subjectId: "push-ups").allSatisfy { $0.instanceId != "done-tue" })
    }

    func testInstanceTenDaysOutIsLaterNotInDays() throws {
        let now = try DomainFixtures.now()
        let origin = SlotLaw.startOfDay(for: now)
        var snapshot = try SeedFactory.buildSeed(now: now)
        let far = try XCTUnwrap(SlotLaw.dayCalendar.date(byAdding: .day, value: 10, to: origin))
        let extra = Instance(
            id: "later-set",
            subjectId: "push-ups",
            when: noonOn(far),
            status: .prepared
        )
        snapshot.instances.append(extra)
        let horizon = SlotLaw.horizon(desk: snapshot, origin: origin)
        let dayKeys = Set(horizon.days.map { SlotLaw.dayKey($0.date) })
        XCTAssertTrue(horizon.later.contains { SlotLaw.isSameDay($0, far) })
        XCTAssertFalse(dayKeys.contains(SlotLaw.dayKey(far)))
        XCTAssertTrue(slots(horizon, subjectId: "push-ups").allSatisfy { $0.instanceId != "later-set" })
    }

    func testCadenceNoneWithoutInstancesHasNoProjections() throws {
        let origin = SlotLaw.startOfDay(for: noon(2026, 8, 12))
        let desk = try desk([subject("gift", cadence: Cadence.none())])
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        XCTAssertEqual(slots(horizon, subjectId: "gift"), [])
        XCTAssertEqual(horizon.later, [])
    }

    func testBikeWindowDoesNotMoveSlotToAnotherDay() throws {
        let now = try DomainFixtures.now()
        let origin = SlotLaw.startOfDay(for: now)
        let desk = try SeedFactory.buildSeed(now: now)
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let real = slots(horizon, subjectId: "bike").filter { $0.instanceId == "bike-open" }
        XCTAssertEqual(real.count, 1)
        XCTAssertTrue(SlotLaw.isSameDay(real[0].date, origin))
        XCTAssertEqual(real[0].kind, .due)
    }

    func testRetiredSubjectShowsRealInstanceWithoutProjections() throws {
        let origin = SlotLaw.startOfDay(for: noon(2026, 8, 12))
        let desk = try desk(
            [subject("old", cadence: Cadence.of(count: 3, period: .week), status: .retired)],
            [Instance(id: "old-open", subjectId: "old", when: noon(2026, 8, 12), status: .prepared)]
        )
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let owned = slots(horizon, subjectId: "old")
        XCTAssertEqual(owned.count, 1)
        XCTAssertEqual(owned[0].instanceId, "old-open")
        XCTAssertEqual(owned[0].kind, .due)
        XCTAssertTrue(owned.allSatisfy { $0.instanceId != nil })
    }

    func testTwoInstancesSameSubjectSameDayBothEmitted() throws {
        let origin = SlotLaw.startOfDay(for: noon(2026, 8, 12))
        let morning = noon(2026, 8, 12)
        let evening = try XCTUnwrap(
            SlotLaw.dayCalendar.date(bySettingHour: 18, minute: 0, second: 0, of: morning)
        )
        let desk = try desk(
            [subject("push-ups", cadence: Cadence.of(count: 3, period: .week))],
            [
                Instance(id: "a", subjectId: "push-ups", when: morning, status: .completed),
                Instance(id: "b", subjectId: "push-ups", when: evening, status: .prepared),
            ]
        )
        let horizon = SlotLaw.horizon(desk: desk, origin: origin)
        let today = slots(horizon, subjectId: "push-ups").filter { SlotLaw.isSameDay($0.date, origin) }
        let real = today.filter { $0.instanceId != nil }
        XCTAssertEqual(Set(real.compactMap(\.instanceId)), ["a", "b"])
        XCTAssertEqual(Set(real.map(\.kind)), [.done, .due])
    }

    func testIsoWeekdayIsMondayZeroNotLocaleFirstWeekday() {
        XCTAssertEqual(SlotLaw.isoWeekdayMondayZero(noon(2026, 8, 10)), 0)
        XCTAssertEqual(SlotLaw.isoWeekdayMondayZero(noon(2026, 8, 15)), 5)
        XCTAssertEqual(SlotLaw.isoWeekdayMondayZero(noon(2026, 8, 16)), 6)
    }
}

private extension SlotLawTests {
    func slots(_ horizon: Horizon, subjectId: String) -> [Slot] {
        horizon.days.flatMap(\.slots).filter { $0.subjectId == subjectId }
    }

    func desk(_ subjects: [Subject], _ instances: [Instance] = []) -> DeskSnapshot {
        DeskSnapshot(subjects: subjects, cues: [], instances: instances, widgets: [])
    }

    func subject(
        _ id: String,
        cadence: Cadence,
        status: SubjectStatus = .active,
        window: TimeWindow? = nil
    ) -> Subject {
        Subject(id: id, title: id, cadence: cadence, window: window, status: status)
    }

    func noon(_ year: Int, _ month: Int, _ day: Int) -> Date {
        var parts = DateComponents()
        parts.year = year
        parts.month = month
        parts.day = day
        parts.hour = 12
        parts.minute = 0
        parts.second = 0
        return SlotLaw.dayCalendar.date(from: parts) ?? Date.distantPast
    }

    func noonOn(_ day: Date) -> Date {
        SlotLaw.dayCalendar.date(bySettingHour: 12, minute: 0, second: 0, of: day) ?? day
    }
}
