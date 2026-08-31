import XCTest
@testable import Facio

/// Mirrors `packages/domain/tests/test_catalog_stepper.py`, plus the one rule
/// the RFC states only about this type: the tile is not a live stepper.
final class StepperLawTests: XCTestCase {
    private let warmup = ["суставная разминка", "5 минут велотренажёра", "два подхода без веса"]

    private func payload(_ current: Int = 0) -> WidgetPayload {
        WidgetPayload(beats: warmup, current: current)
    }

    func testWalkingTheBeatsStopsAtBothEnds() {
        let base = payload()
        XCTAssertEqual(StepperLaw.beat(of: base), warmup[0])
        XCTAssertTrue(StepperLaw.isFirst(base))
        XCTAssertFalse(StepperLaw.isLast(base))

        let second = StepperLaw.forward(base)
        XCTAssertEqual(StepperLaw.position(of: second), 1)
        // Pure: the payload handed in did not move.
        XCTAssertEqual(StepperLaw.position(of: base), 0)

        let last = StepperLaw.forward(StepperLaw.forward(second))
        XCTAssertTrue(StepperLaw.isLast(last))
        // The last beat does not roll over into the first.
        XCTAssertEqual(StepperLaw.forward(last), last)

        let first = StepperLaw.back(StepperLaw.back(StepperLaw.back(last)))
        XCTAssertEqual(StepperLaw.position(of: first), 0)
        XCTAssertEqual(StepperLaw.back(first), first)
    }

    func testAPositionPastTheEndReadsAsTheLastBeat() {
        let stale = payload(9)
        XCTAssertEqual(StepperLaw.position(of: stale), 2)
        XCTAssertEqual(StepperLaw.beat(of: stale), warmup[2])
    }

    func testAStepperWithNoBeatsStandsAtZeroAndDoesNotMove() {
        let empty = WidgetPayload()
        XCTAssertEqual(StepperLaw.position(of: empty), 0)
        XCTAssertNil(StepperLaw.beat(of: empty))
        XCTAssertFalse(StepperLaw.isLast(empty))
        XCTAssertEqual(StepperLaw.forward(empty), empty)
        XCTAssertEqual(StepperLaw.back(empty), empty)
        XCTAssertEqual(StepperLaw.finish(empty), empty)
    }

    func testFinishLeavesTheSequenceOnItsLastBeat() {
        XCTAssertTrue(StepperLaw.isLast(StepperLaw.finish(payload())))
    }

    /// 04: «Today/Lifetime: checklist/timer may be interactive on the tile;
    /// stepper is not.» This is where that sentence lives in the client.
    func testOnlyTheStepperTileRefusesToRunLive() {
        XCTAssertFalse(WidgetType.stepper.tileRunsLive)
        for type in [WidgetType.counter, .tick, .reminder, .checklist, .timer] {
            XCTAssertTrue(type.tileRunsLive, "\(type.rawValue)")
        }
        // Every catalog type has a runtime now, so all of them are on the lid.
        for type in [WidgetType.counter, .tick, .reminder, .checklist, .timer, .stepper] {
            XCTAssertTrue(type.showsOnLid, "\(type.rawValue)")
        }
    }

    func testBeatsSurviveTheWire() throws {
        let data = try FacioJSON.encoder.encode(payload(1))
        let text = try XCTUnwrap(String(data: data, encoding: .utf8))
        XCTAssertTrue(text.contains("beats"))
        XCTAssertTrue(text.contains("current"))
        let decoded = try FacioJSON.decoder.decode(WidgetPayload.self, from: data)
        XCTAssertEqual(StepperLaw.beat(of: decoded), warmup[1])
    }

    func testTheDoTimeCueReachesAStepper() {
        let cues = [
            CueLaw.addCue(id: "warmup-cue", subjectId: "warmup", kind: .correction, text: "не тяни на холодную")
        ]
        XCTAssertEqual(CueLaw.surfaceCue(in: cues, subjectId: "warmup", widgetType: .stepper)?.surface, .doTime)
    }
}
