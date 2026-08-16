import XCTest
@testable import Facio

final class ReminderClockTests: XCTestCase {
    func testClosing22FiresAt19() throws {
        let window = ReminderClock.windowFromClosing(ClockTime(hour: 22, minute: 0))
        XCTAssertEqual(window.closesAt?.hour, 22)
        XCTAssertEqual(window.latestBy.hour, 19)
        let day = try XCTUnwrap(FacioJSON.date(from: "2026-08-15T12:00:00"))
        let fired = ReminderClock.reminderFireAt(window: window, on: day)
        let parts = Calendar.current.dateComponents([.year, .month, .day, .hour, .minute], from: fired)
        XCTAssertEqual(parts.hour, 19)
        XCTAssertEqual(parts.minute, 0)
        XCTAssertEqual(parts.day, 15)
    }

    func testBikeFixtureWindowMatchesFoundingRule() throws {
        let bike = try DomainFixtures.subject("bike")
        let closes = try XCTUnwrap(bike.window?.closesAt)
        let derived = ReminderClock.windowFromClosing(closes)
        XCTAssertEqual(derived.latestBy, bike.window?.latestBy)
        let day = try XCTUnwrap(FacioJSON.date(from: "2026-08-15T00:00:00"))
        let fired = ReminderClock.reminderFireAt(window: try XCTUnwrap(bike.window), on: day)
        XCTAssertEqual(FacioJSON.string(from: fired), "2026-08-15T19:00:00")
    }

    func testGymHoursAreOpenToClosing() throws {
        let window = ReminderClock.windowFromClosing(ClockTime(hour: 22, minute: 0))
        let day = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let range = ReminderClock.gymHours(window: window, on: day)
        XCTAssertEqual(ReminderClock.clock(from: range.lowerBound), ReminderClock.defaultGymOpens)
        XCTAssertEqual(ReminderClock.clock(from: range.upperBound).hour, 22)
        XCTAssertEqual(ReminderClock.clamp(ClockTime(hour: 5, minute: 0), to: window), ReminderClock.defaultGymOpens)
        XCTAssertEqual(ReminderClock.clamp(ClockTime(hour: 23, minute: 0), to: window).hour, 22)
        XCTAssertEqual(ReminderClock.clamp(ClockTime(hour: 18, minute: 30), to: window), ClockTime(hour: 18, minute: 30))
        XCTAssertEqual(ReminderClock.clamp(ClockTime(hour: 20, minute: 0), to: window), ClockTime(hour: 20, minute: 0))
        XCTAssertEqual(ReminderClock.gymHourRange(window: window), 6...22)
    }
}
