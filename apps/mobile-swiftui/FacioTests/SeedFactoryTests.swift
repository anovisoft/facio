import XCTest
@testable import Facio

final class SeedFactoryTests: XCTestCase {
    func testSeedPutsFoundingSubjectsOnToday() throws {
        let now = try DomainFixtures.now()
        let seed = try SeedFactory.buildSeed(now: now)
        XCTAssertEqual(
            Set(seed.widgets.filter { $0.section == .today }.map(\.id)),
            ["push-ups-counter", "vegetables-tick"]
        )
        XCTAssertEqual(seed.widgets.first { $0.id == "bike-reminder" }?.section, .lifetime)
        let cue = try XCTUnwrap(CueLaw.doTimeCue(in: seed.cues, subjectId: "push-ups"))
        XCTAssertEqual(cue.text, "держи корпус и ягодицы")
        XCTAssertEqual(cue.surface, .doTime)
    }

    func testSeedSurfacesBikeDrift() throws {
        let now = try DomainFixtures.now()
        let seed = try SeedFactory.buildSeed(now: now)
        let silent = try XCTUnwrap(seed.instances.first { $0.id == "bike-silent" })
        XCTAssertEqual(silent.status, .completed)
        let days = DriftLaw.silenceDays(
            of: try XCTUnwrap(seed.subjects.first { $0.id == "bike" }),
            in: seed.instances,
            now: now
        )
        XCTAssertEqual(days, 21)
        let projection = LidProjectionLaw.project(
            now: now,
            subjects: seed.subjects,
            instances: seed.instances,
            widgets: seed.widgets
        )
        XCTAssertEqual(projection.driftCard?.subjectId, "bike")
        XCTAssertEqual(projection.driftCard?.silentDays, 21)
        XCTAssertEqual(projection.driftCard?.offer, .moveToToday)
        XCTAssertTrue(projection.today.contains { $0.kind == "drift" })
        XCTAssertFalse(projection.today.contains { item in
            if case .widget(_, let widget) = item { return widget.id == "bike-reminder" }
            return false
        })
    }

    func testEnsureFoundingIsIdempotent() throws {
        let now = try DomainFixtures.now()
        let first = try SeedFactory.buildSeed(now: now)
        let second = try SeedFactory.ensureFounding(in: first, now: now)
        XCTAssertEqual(first, second)
    }

    func testEnsureDriftDoesNotInventSilenceWhenBikeAlreadyDone() throws {
        let now = try DomainFixtures.now()
        var snapshot = try SeedFactory.buildSeed(now: now)
        snapshot.instances.removeAll { $0.id == "bike-silent" }
        snapshot.subjects = snapshot.subjects.map { subject in
            var next = subject
            if next.id == "bike" {
                next.instanceIds.removeAll { $0 == "bike-silent" }
            }
            return next
        }
        let recent = try XCTUnwrap(FacioJSON.date(from: "2026-08-14T18:00:00"))
        snapshot.instances.append(Instance(id: "bike-recent", subjectId: "bike", when: recent, status: .completed))
        snapshot.widgets = snapshot.widgets.map { widget in
            var next = widget
            if next.id == "bike-reminder" { next.section = .today }
            return next
        }
        let migrated = try SeedFactory.ensureDrift(in: snapshot, now: now)
        XCTAssertNil(migrated.instances.first { $0.id == "bike-silent" })
        XCTAssertEqual(migrated.widgets.first { $0.id == "bike-reminder" }?.section, .today)
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
