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
}
