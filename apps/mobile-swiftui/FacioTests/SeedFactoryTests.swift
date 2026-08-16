import XCTest
@testable import Facio

final class SeedFactoryTests: XCTestCase {
    func testSeedPutsFoundingSubjectsOnToday() throws {
        let now = try DomainFixtures.now()
        let seed = try SeedFactory.buildSeed(now: now)
        XCTAssertEqual(Set(seed.widgets.map(\.section)), [.today])
        XCTAssertEqual(Set(seed.widgets.map(\.id)), ["push-ups-counter", "vegetables-tick", "bike-reminder"])
        let cue = try XCTUnwrap(CueLaw.doTimeCue(in: seed.cues, subjectId: "push-ups"))
        XCTAssertEqual(cue.text, "держи корпус и ягодицы")
        XCTAssertEqual(cue.surface, .doTime)
    }

    func testSeedBikeWindowFiresAt19FromGym22() throws {
        let now = try DomainFixtures.now()
        let seed = try SeedFactory.buildSeed(now: now)
        let bike = try XCTUnwrap(seed.subjects.first { $0.id == "bike" })
        let window = try XCTUnwrap(bike.window)
        XCTAssertEqual(window.closesAt?.hour, 22)
        XCTAssertEqual(window.latestBy.hour, 19)
        let timing = try XCTUnwrap(CueLaw.timingCue(in: seed.cues, subjectId: "bike"))
        XCTAssertEqual(timing.text, "зал до 22")
        XCTAssertEqual(timing.surface, .timing)
        let widget = try XCTUnwrap(seed.widgets.first { $0.id == "bike-reminder" })
        XCTAssertEqual(widget.type, .reminder)
        XCTAssertEqual(widget.tileSize, .wide)
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
        XCTAssertEqual(widget.payload.fireAt, fireAt)
        XCTAssertEqual(widget.when, fireAt)
    }

    func testEnsureBikeIsIdempotent() throws {
        let now = try DomainFixtures.now()
        let first = try SeedFactory.buildSeed(now: now)
        let second = try SeedFactory.ensureBike(in: first, now: now)
        XCTAssertEqual(first, second)
    }

    func testEnsureBikeBackfillsMissingWindow() throws {
        let now = try DomainFixtures.now()
        var snapshot = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(snapshot.subjects.firstIndex { $0.id == "bike" })
        snapshot.subjects[index].window = nil
        let widgetIndex = try XCTUnwrap(snapshot.widgets.firstIndex { $0.id == "bike-reminder" })
        snapshot.widgets[widgetIndex].payload.fireAt = now
        snapshot.widgets[widgetIndex].when = now
        let migrated = try SeedFactory.ensureBike(in: snapshot, now: now)
        XCTAssertEqual(migrated.subjects[index].window?.latestBy.hour, 19)
        XCTAssertEqual(migrated.subjects[index].window?.closesAt?.hour, 22)
        let fireAt = ReminderClock.reminderFireAt(window: try XCTUnwrap(migrated.subjects[index].window), on: now)
        XCTAssertEqual(migrated.widgets[widgetIndex].payload.fireAt, fireAt)
        XCTAssertEqual(migrated.widgets[widgetIndex].when, fireAt)
    }

    func testEnsureBikePromotesBannerToWide() throws {
        let now = try DomainFixtures.now()
        var snapshot = try SeedFactory.buildSeed(now: now)
        let index = try XCTUnwrap(snapshot.widgets.firstIndex { $0.id == "bike-reminder" })
        snapshot.widgets[index].tileSize = .banner
        let migrated = try SeedFactory.ensureBike(in: snapshot, now: now)
        XCTAssertEqual(migrated.widgets[index].tileSize, .wide)
    }
}
