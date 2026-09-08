import XCTest
@testable import Facio

final class ModelTests: XCTestCase {
    func testPushUpsFixture() throws {
        let push = try DomainFixtures.subject("push-ups")
        let cues = try DomainFixtures.cues()
        XCTAssertEqual(push.cadence.count, 3)
        XCTAssertEqual(push.cadence.period, .week)
        XCTAssertEqual(push.target?.current, 28)
        XCTAssertEqual(push.target?.goal, 30)
        let brace = try XCTUnwrap(cues.first { $0.id == "push-ups-brace" })
        XCTAssertEqual(brace.kind, .correction)
        XCTAssertEqual(brace.surface, .doTime)
        XCTAssertEqual(brace.text, "brace the core and the glutes")
        XCTAssertTrue(push.cueIds.contains("push-ups-brace"))
    }

    func testBikeFixtureWindow() throws {
        let bike = try DomainFixtures.subject("bike")
        let cues = try DomainFixtures.cues()
        XCTAssertEqual(bike.cadence.count, 2)
        XCTAssertEqual(bike.window?.closesAt?.hour, 22)
        XCTAssertEqual(bike.window?.latestBy.hour, 19)
        let timing = try XCTUnwrap(cues.first { $0.id == "bike-gym-hours" })
        XCTAssertEqual(timing.surface, .timing)
        XCTAssertEqual(timing.text, "зал до 22")
    }

    func testVegetablesIsDailyIsh() throws {
        let vegetables = try DomainFixtures.subject("vegetables")
        XCTAssertEqual(vegetables.cadence.count, 1)
        XCTAssertEqual(vegetables.cadence.period, .day)
    }

    func testCadenceNoneRejectsCount() {
        XCTAssertThrowsError(try Cadence(count: 1, period: .none))
    }

    func testCadenceCountRequiresCount() {
        XCTAssertThrowsError(try Cadence(count: nil, period: .week))
    }

    func testCueWithoutSurfaceFails() {
        let data = Data(#"{"id":"orphan","subject_id":"push-ups","kind":"correction","text":"brace"}"#.utf8)
        XCTAssertThrowsError(try FacioJSON.decoder.decode(Cue.self, from: data))
    }

    func testQuoteIsTextNotOffset() {
        let data = Data(#"{"id":"bad","subject_id":"push-ups","kind":"clarification","text":"x","quote":14,"surface":"on-demand"}"#.utf8)
        XCTAssertThrowsError(try FacioJSON.decoder.decode(Cue.self, from: data))
    }

    func testRetireAndShrinkKeepInstancesAndCues() throws {
        var marked = try DomainFixtures.subject("push-ups")
        marked.instanceIds = ["a"]
        let shrunk = SubjectLaw.shrink(marked)
        let retired = SubjectLaw.retire(marked)
        XCTAssertEqual(shrunk.status, .shrunk)
        XCTAssertEqual(retired.status, .retired)
        XCTAssertEqual(shrunk.instanceIds, marked.instanceIds)
        XCTAssertEqual(retired.instanceIds, marked.instanceIds)
        XCTAssertEqual(shrunk.cueIds, marked.cueIds)
    }

    func testFreezeAndThawKeepCadenceTargetInstancesAndCues() throws {
        var marked = try DomainFixtures.subject("push-ups")
        marked.instanceIds = ["a"]
        let now = try DomainFixtures.now()
        let frozen = SubjectLaw.freeze(marked, now: now)
        XCTAssertEqual(frozen.status, .paused)
        XCTAssertEqual(frozen.pausedAt, now)
        XCTAssertEqual(frozen.cadence, marked.cadence)
        XCTAssertEqual(frozen.target, marked.target)
        XCTAssertEqual(frozen.instanceIds, marked.instanceIds)
        XCTAssertEqual(frozen.cueIds, marked.cueIds)
        let later = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T09:00:00"))
        let again = SubjectLaw.freeze(frozen, now: later)
        XCTAssertEqual(again.pausedAt, later)
        XCTAssertEqual(again.cadence, marked.cadence)
        let thawed = SubjectLaw.thaw(frozen)
        XCTAssertEqual(thawed.status, .active)
        XCTAssertNil(thawed.pausedAt)
        XCTAssertEqual(thawed.cadence, marked.cadence)
        XCTAssertEqual(thawed.target, marked.target)
        XCTAssertEqual(thawed.instanceIds, marked.instanceIds)
        XCTAssertEqual(thawed.cueIds, marked.cueIds)
        // Two calendar days at the same hour. This used to assert a fixed
        // 172 800 seconds, which is the same thing only on nights when the
        // clock does not move — and it was the reason the phone and
        // `packages/domain` disagreed by an hour twice a year.
        XCTAssertEqual(
            SubjectLaw.pauseCheckInAt(now),
            Calendar.current.date(byAdding: .day, value: SubjectLaw.pauseCheckInDays, to: now)
        )
    }

    func testOldSubjectJsonWithoutPausedAtDecodes() throws {
        let json = Data(
            #"{"id":"bike","title":"exercise bike","cadence":{"count":2,"period":"week"},"status":"active"}"#.utf8
        )
        let subject = try FacioJSON.decoder.decode(Subject.self, from: json)
        XCTAssertNil(subject.pausedAt)
        XCTAssertEqual(subject.status, .active)
    }
}
