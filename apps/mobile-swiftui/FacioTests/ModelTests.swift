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
}
