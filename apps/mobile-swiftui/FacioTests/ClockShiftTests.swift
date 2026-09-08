import XCTest
@testable import Facio

/// The clocks move, and the phone travels.
///
/// This is a product about **hours**, and until now nothing checked what the
/// law does on the two days a year the hour is not a fixed thing, or when the
/// device wakes up in another zone. Time is substituted, never waited for:
/// `NSTimeZone.default` is the zone the law reads through `Calendar.current`,
/// and every date here is a wall clock in that zone.
///
/// The rule the whole file measures is one sentence: **a stated hour is a wall
/// clock**. «в 19» means 19:00 on the day it falls on, in the zone the person
/// is standing in — not 19:00 minus an offset, and not 20:00 because the night
/// before was an hour short.
@MainActor
final class ClockShiftTests: XCTestCase {
    private var original: TimeZone!

    override func setUp() {
        super.setUp()
        original = NSTimeZone.default
    }

    override func tearDown() {
        NSTimeZone.default = original
        super.tearDown()
    }

    // MARK: - the clocks move under a standing hour

    /// Berlin jumps 02:00 → 03:00 on 2026-03-29. The 19:00 alarm must ring at
    /// 19:00 on that day and on the ones either side of it.
    func testAStandingHourSurvivesSpringForward() throws {
        use("Europe/Berlin")
        let desk = try dailyReminderDesk(hour: 19, now: at("2026-03-27T09:00:00"))
        for day in ["2026-03-28", "2026-03-29", "2026-03-30"] {
            let fired = alarms(desk, on: at("\(day)T09:00:00"))
            XCTAssertEqual(fired.count, ReminderScheduler.horizonDays, day)
            XCTAssertTrue(
                fired.allSatisfy { ReminderClock.clock(from: $0.fireAt) == ClockTime(hour: 19, minute: 0) },
                "\(day): \(fired.map { FacioJSON.string(from: $0.fireAt) })"
            )
        }
    }

    /// And 03:00 → 02:00 on 2026-10-25, the day that has an hour twice.
    func testAStandingHourSurvivesFallBack() throws {
        use("Europe/Berlin")
        let desk = try dailyReminderDesk(hour: 19, now: at("2026-10-23T09:00:00"))
        for day in ["2026-10-24", "2026-10-25", "2026-10-26"] {
            let fired = alarms(desk, on: at("\(day)T09:00:00"))
            XCTAssertEqual(fired.count, ReminderScheduler.horizonDays, day)
            XCTAssertTrue(
                fired.allSatisfy { ReminderClock.clock(from: $0.fireAt) == ClockTime(hour: 19, minute: 0) },
                "\(day): \(fired.map { FacioJSON.string(from: $0.fireAt) })"
            )
        }
    }

    // MARK: - the zone where midnight does not exist

    /// Havana moves its clock **at 00:00** on 2026-03-08, so that day has no
    /// midnight and `startOfDay` is 01:00. Measured before the fix: on that one
    /// day the horizon collapsed — the strips were keyed at 01:00 while the
    /// projections landed on the following midnights, so every day but today
    /// lost its slots, the Inspect calendar went blank for the week, and a
    /// daily practice went from three pending alarms to **one**.
    func testTheHorizonKeepsSevenDaysWhereMidnightDoesNotExist() throws {
        use("America/Havana")
        let now = at("2026-03-08T09:00:00")
        let desk = try dailyReminderDesk(hour: 19, now: at("2026-03-07T09:00:00"))
        let horizon = SlotLaw.horizon(desk: desk, origin: now)

        XCTAssertEqual(horizon.days.count, SlotLaw.horizonLength)
        XCTAssertEqual(Set(horizon.days.map(\.date)).count, SlotLaw.horizonLength)
        // Every strip is the first moment of its own day, and no two strips
        // are the same day.
        XCTAssertEqual(horizon.days.map(\.date), horizon.days.map { SlotLaw.startOfDay(for: $0.date) })
        XCTAssertEqual(SlotLaw.dueDays(subjectId: "bike", in: horizon.days).count, SlotLaw.horizonLength)
    }

    func testAlarmsSurviveTheDayWithoutAMidnight() throws {
        use("America/Havana")
        let desk = try dailyReminderDesk(hour: 19, now: at("2026-03-07T09:00:00"))
        let fired = alarms(desk, on: at("2026-03-08T09:00:00"))
        XCTAssertEqual(fired.count, ReminderScheduler.horizonDays)
        XCTAssertTrue(fired.allSatisfy { ReminderClock.clock(from: $0.fireAt) == ClockTime(hour: 19, minute: 0) })
        // The day segment of an id names the day the alarm actually fires on.
        XCTAssertEqual(
            fired.map(\.id).sorted(),
            [
                ReminderScheduler.alarmId(widgetId: "bike-reminder"),
                ReminderScheduler.alarmId(widgetId: "bike-reminder", on: at("2026-03-09T12:00:00")),
                ReminderScheduler.alarmId(widgetId: "bike-reminder", on: at("2026-03-10T12:00:00")),
            ].sorted()
        )
    }

    // MARK: - the check-in two days after a pause

    /// «через два дня» is two days, not 48 hours. Frozen at 19:00 on the Friday
    /// before the clocks go forward, the check-in was landing at **20:00** —
    /// and the shared law in `packages/domain` says 19:00, so the two ports
    /// disagreed on a Sunday twice a year.
    func testThePauseCheckInIsTwoDaysNotFortyEightHours() {
        use("Europe/Berlin")
        let paused = at("2026-03-27T19:00:00")
        XCTAssertEqual(SubjectLaw.pauseCheckInAt(paused), at("2026-03-29T19:00:00"))
    }

    func testThePauseCheckInIsTwoDaysAcrossFallBackToo() {
        use("Europe/Berlin")
        let paused = at("2026-10-23T19:00:00")
        XCTAssertEqual(SubjectLaw.pauseCheckInAt(paused), at("2026-10-25T19:00:00"))
    }

    // MARK: - the phone changes zone

    /// A desk written in Shanghai and opened in New York keeps its **wall
    /// clock**: «в 19» is 19:00 where the person is standing, which is what a
    /// window means (04). Nothing here is a UTC instant that drifts to 06:00.
    func testAWindowTravelsAsAWallClock() throws {
        use("Asia/Shanghai")
        let written = try dailyReminderDesk(hour: 19, now: at("2026-09-08T09:00:00"))
        let encoded = try FacioJSON.encoder.encode(written)

        use("America/New_York")
        let read = try FacioJSON.decoder.decode(DeskSnapshot.self, from: encoded)
        XCTAssertEqual(read.subjects.first?.window?.hours, [ClockTime(hour: 19, minute: 0)])
        let fired = alarms(read, on: at("2026-09-08T09:00:00"))
        XCTAssertEqual(fired.count, ReminderScheduler.horizonDays)
        XCTAssertTrue(fired.allSatisfy { ReminderClock.clock(from: $0.fireAt) == ClockTime(hour: 19, minute: 0) })
    }

    /// The day math and the hour math must read the zone through the **same**
    /// door. They did not: `SlotLaw.dayCalendar` took `TimeZone.current` while
    /// everything else takes `Calendar.current`, and inside one process those
    /// two were measured 13 hours apart — `startOfDay` on one date, the hour
    /// laid on another.
    func testTheDayMathAndTheHourMathAgreeOnTheZone() {
        for zone in ["America/Havana", "Europe/Berlin", "Asia/Shanghai", "Pacific/Kiritimati"] {
            use(zone)
            XCTAssertEqual(SlotLaw.dayCalendar.timeZone, Calendar.current.timeZone, zone)
        }
    }

    // MARK: -

    private func use(_ id: String) {
        NSTimeZone.default = TimeZone(identifier: id)!
    }

    private func at(_ iso: String) -> Date {
        FacioJSON.date(from: iso)!
    }

    private func alarms(_ snapshot: DeskSnapshot, on when: Date) -> [ReminderAlarm] {
        ReminderScheduler.alarms(from: snapshot, now: when)
    }

    private func dailyReminderDesk(hour: Int, now: Date) throws -> DeskSnapshot {
        let window = TimeWindow(hours: [ClockTime(hour: hour, minute: 0)])
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
        let subject = Subject(
            id: "bike",
            title: "велосипед",
            cadence: try Cadence.of(count: 1, period: .day),
            window: window,
            instanceIds: ["bike-open"]
        )
        return DeskSnapshot(
            subjects: [subject],
            cues: [],
            instances: [Instance(id: "bike-open", subjectId: "bike", when: fireAt, status: .prepared)],
            widgets: [
                Widget(
                    id: "bike-reminder",
                    type: .reminder,
                    title: "велосипед",
                    payload: WidgetPayload(fireAt: fireAt),
                    status: .ready,
                    when: fireAt,
                    section: .today,
                    subjectId: "bike",
                    instanceId: "bike-open",
                    tileSize: .wide
                )
            ]
        )
    }
}
