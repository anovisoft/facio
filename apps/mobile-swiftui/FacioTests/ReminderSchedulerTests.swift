import XCTest
@testable import Facio

final class ReminderSchedulerTests: XCTestCase {
    func testAlarmsComeFromWindowNotFromNow() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let seed = try SeedFactory.buildSeed(now: now)
        let alarms = ReminderScheduler.alarms(from: seed, now: now)
        let alarm = try XCTUnwrap(alarms.first)
        XCTAssertEqual(alarm.id, ReminderScheduler.alarmId(widgetId: "bike-reminder"))
        XCTAssertEqual(alarm.title, DisplayCopy.title(subjectId: "bike", stored: "exercise bike"))
        XCTAssertTrue(alarm.body.contains("19:00"))
        XCTAssertTrue(alarm.body.contains("зал до 22"))
        let fireHour = Calendar.current.component(.hour, from: alarm.fireAt)
        XCTAssertEqual(fireHour, 19)
    }

    func testPastFireAtIsNotScheduled() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T20:00:00"))
        let seed = try SeedFactory.buildSeed(now: now)
        XCTAssertTrue(ReminderScheduler.alarms(from: seed, now: now).isEmpty)
    }

    func testDoneReminderIsNotScheduled() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.widgets.firstIndex { $0.id == "bike-reminder" })
        seed.widgets[index].status = .done
        XCTAssertTrue(ReminderScheduler.alarms(from: seed, now: now).isEmpty)
    }

    func testRetiredSubjectIsNotScheduled() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.subjects.firstIndex { $0.id == "bike" })
        seed.subjects[index].status = .retired
        XCTAssertTrue(ReminderScheduler.alarms(from: seed, now: now).isEmpty)
    }

    func testFrozenSubjectSilencesGymAndSchedulesCheckIn() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.subjects.firstIndex { $0.id == "bike" })
        seed.subjects[index] = SubjectLaw.freeze(seed.subjects[index], now: now)
        let alarms = ReminderScheduler.alarms(from: seed, now: now)
        XCTAssertFalse(alarms.contains { $0.id == ReminderScheduler.alarmId(widgetId: "bike-reminder") })
        let checkIn = try XCTUnwrap(alarms.first { $0.id == ReminderScheduler.checkInAlarmId(subjectId: "bike") })
        XCTAssertEqual(checkIn.fireAt, SubjectLaw.pauseCheckInAt(now))
        XCTAssertEqual(checkIn.body, DisplayCopy.pauseCheckInBody)
        XCTAssertEqual(
            checkIn.title,
            DisplayCopy.title(subjectId: "bike", stored: seed.subjects[index].title)
        )
    }

    func testThawRemovesCheckIn() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.subjects.firstIndex { $0.id == "bike" })
        seed.subjects[index] = SubjectLaw.freeze(seed.subjects[index], now: now)
        XCTAssertTrue(
            ReminderScheduler.alarms(from: seed, now: now)
                .contains { $0.id == ReminderScheduler.checkInAlarmId(subjectId: "bike") }
        )
        seed.subjects[index] = SubjectLaw.thaw(seed.subjects[index])
        XCTAssertFalse(
            ReminderScheduler.alarms(from: seed, now: now)
                .contains { $0.id == ReminderScheduler.checkInAlarmId(subjectId: "bike") }
        )
    }

    // MARK: - Q34: an alarm on every hour the person named

    func testEveryStatedHourGetsItsOwnAlarm() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T09:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.subjects.firstIndex { $0.id == "bike" })
        let hours = [
            ClockTime(hour: 10, minute: 0),
            ClockTime(hour: 12, minute: 0),
            ClockTime(hour: 15, minute: 0),
            ClockTime(hour: 16, minute: 30),
            ClockTime(hour: 18, minute: 0),
            ClockTime(hour: 21, minute: 0),
            ClockTime(hour: 22, minute: 0),
        ]
        seed.subjects[index].window = TimeWindow(hours: hours)
        let alarms = ReminderScheduler.alarms(from: seed, now: now)
            .filter { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "bike-reminder")) }
        XCTAssertEqual(alarms.count, 7)
        // One id per hour: sharing one would let the second overwrite the first.
        XCTAssertEqual(Set(alarms.map(\.id)).count, 7)
        let clocks = alarms.map { ReminderClock.clock(from: $0.fireAt) }.sorted()
        XCTAssertEqual(clocks, hours)
        // Each alarm says its own hour, not the first of the day.
        let half = try XCTUnwrap(alarms.first { $0.id.hasSuffix("16:30") })
        XCTAssertTrue(half.body.contains("16:30"))
    }

    func testHoursAlreadyPastAreNotScheduled() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T17:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.subjects.firstIndex { $0.id == "bike" })
        seed.subjects[index].window = TimeWindow(hours: [
            ClockTime(hour: 10, minute: 0),
            ClockTime(hour: 18, minute: 0),
            ClockTime(hour: 21, minute: 0),
        ])
        let alarms = ReminderScheduler.alarms(from: seed, now: now)
            .filter { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "bike-reminder")) }
        XCTAssertEqual(alarms.map { ReminderClock.clock(from: $0.fireAt).hour }.sorted(), [18, 21])
    }

    func testASingleHourKeepsThePlainAlarmId() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let seed = try SeedFactory.buildSeed(now: now)
        let alarms = ReminderScheduler.alarms(from: seed, now: now)
        XCTAssertEqual(alarms.first?.id, ReminderScheduler.alarmId(widgetId: "bike-reminder"))
    }

    func testAPausedPracticeIsSilentOnEveryHour() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T09:00:00"))
        var seed = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(seed.subjects.firstIndex { $0.id == "bike" })
        seed.subjects[index].window = TimeWindow(hours: [
            ClockTime(hour: 10, minute: 0),
            ClockTime(hour: 18, minute: 0),
        ])
        seed.subjects[index] = SubjectLaw.freeze(seed.subjects[index], now: now)
        let alarms = ReminderScheduler.alarms(from: seed, now: now)
        XCTAssertFalse(alarms.contains { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "bike-reminder")) })
    }
}
