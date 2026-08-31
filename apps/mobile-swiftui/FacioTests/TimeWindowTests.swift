import XCTest
@testable import Facio

/// Q34: a window may hold several stated hours, and a desk written before it
/// still opens.
final class TimeWindowTests: XCTestCase {
    func testAWindowWrittenBeforeQ34StillOpens() throws {
        let json = Data(#"{"latest_by":"19:00:00","closes_at":"22:00:00"}"#.utf8)
        let window = try FacioJSON.decoder.decode(TimeWindow.self, from: json)
        XCTAssertEqual(window.hours, [ClockTime(hour: 19, minute: 0)])
        XCTAssertEqual(window.latestBy, ClockTime(hour: 19, minute: 0))
        XCTAssertEqual(window.closesAt, ClockTime(hour: 22, minute: 0))
    }

    func testAWindowGoesBackOutInTheShapeAnOlderReaderKnows() throws {
        let window = TimeWindow(
            hours: [ClockTime(hour: 12, minute: 0), ClockTime(hour: 10, minute: 0)],
            closesAt: ClockTime(hour: 22, minute: 0)
        )
        let written = try FacioJSON.encoder.encode(window)
        let raw = try XCTUnwrap(
            JSONSerialization.jsonObject(with: written) as? [String: Any]
        )
        XCTAssertEqual(raw["latest_by"] as? String, "10:00:00")
        XCTAssertEqual(raw["hours"] as? [String], ["10:00:00", "12:00:00"])
        // And it round-trips back to the same window.
        XCTAssertEqual(try FacioJSON.decoder.decode(TimeWindow.self, from: written), window)
    }

    func testAWholeDeskWrittenBeforeQ34StillOpens() throws {
        let json = Data(#"""
        {
          "subjects": [
            {
              "id": "bike",
              "title": "exercise bike",
              "cadence": {"count": 2, "period": "week"},
              "window": {"latest_by": "19:00:00", "closes_at": "22:00:00"}
            }
          ],
          "cues": [],
          "instances": [],
          "widgets": []
        }
        """#.utf8)
        let snapshot = try FacioJSON.decoder.decode(DeskSnapshot.self, from: json)
        let window = try XCTUnwrap(snapshot.subjects.first?.window)
        XCTAssertEqual(window.hours, [ClockTime(hour: 19, minute: 0)])
        XCTAssertEqual(window.latestBy, ClockTime(hour: 19, minute: 0))
    }

    func testHoursAreOrderedAndTheSameHourTwiceIsOneHour() {
        var window = TimeWindow(hours: [ClockTime(hour: 22, minute: 0), ClockTime(hour: 10, minute: 0)])
        window.addHour(ClockTime(hour: 16, minute: 30))
        window.addHour(ClockTime(hour: 10, minute: 0))
        XCTAssertEqual(
            window.hours,
            [
                ClockTime(hour: 10, minute: 0),
                ClockTime(hour: 16, minute: 30),
                ClockTime(hour: 22, minute: 0),
            ]
        )
        XCTAssertEqual(window.latestBy, ClockTime(hour: 10, minute: 0))
    }

    func testDroppingTheLastHourIsRefused() {
        var window = TimeWindow(latestBy: ClockTime(hour: 19, minute: 0))
        XCTAssertFalse(window.removeHour(ClockTime(hour: 19, minute: 0)))
        XCTAssertEqual(window.hours, [ClockTime(hour: 19, minute: 0)])
    }

    func testTheNextHourIsTheNearestOneStillAhead() {
        let window = TimeWindow(hours: [
            ClockTime(hour: 10, minute: 0),
            ClockTime(hour: 16, minute: 30),
            ClockTime(hour: 22, minute: 0),
        ])
        XCTAssertEqual(window.nextHour(after: ClockTime(hour: 9, minute: 0)), ClockTime(hour: 10, minute: 0))
        XCTAssertEqual(window.nextHour(after: ClockTime(hour: 15, minute: 40)), ClockTime(hour: 16, minute: 30))
        // The day is spent: the face falls back to the first hour of the next.
        XCTAssertEqual(window.nextHour(after: ClockTime(hour: 23, minute: 0)), ClockTime(hour: 10, minute: 0))
        XCTAssertEqual(window.hoursAfter(ClockTime(hour: 10, minute: 0)).count, 2)
    }

    func testTheDeadlineLineNamesTheHourBeingAskedAboutNow() throws {
        let window = TimeWindow(hours: [
            ClockTime(hour: 10, minute: 0),
            ClockTime(hour: 16, minute: 30),
        ])
        let afternoon = try XCTUnwrap(FacioJSON.date(from: "2026-08-30T15:40:00"))
        XCTAssertTrue(DisplayCopy.succeedBy(window, now: afternoon).contains("16:30"))
        let morning = try XCTUnwrap(FacioJSON.date(from: "2026-08-30T09:00:00"))
        XCTAssertTrue(DisplayCopy.succeedBy(window, now: morning).contains("10:00"))
    }

    func testEditingTheHourInFrontOfYouLeavesTheOthersAlone() {
        var window = TimeWindow(hours: [
            ClockTime(hour: 10, minute: 0),
            ClockTime(hour: 12, minute: 0),
            ClockTime(hour: 18, minute: 0),
        ])
        window.replaceHour(ClockTime(hour: 12, minute: 0), with: ClockTime(hour: 13, minute: 0))
        XCTAssertEqual(
            window.hours,
            [
                ClockTime(hour: 10, minute: 0),
                ClockTime(hour: 13, minute: 0),
                ClockTime(hour: 18, minute: 0),
            ]
        )
    }
}
