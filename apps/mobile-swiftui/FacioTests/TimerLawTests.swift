import XCTest
@testable import Facio

/// Mirrors `packages/domain/tests/test_catalog_timer.py`. Elapsed seconds are
/// arithmetic over the moment the run began — a divergence from the Python
/// side is a release hole.
final class TimerLawTests: XCTestCase {
    private let now = FacioJSON.date(from: "2026-08-15T12:00:00")!
    private let tenMinutes = 600

    func testElapsedComesFromTheMomentTheRunBegan() {
        let payload = WidgetPayload(seconds: tenMinutes, elapsed: 0)
        XCTAssertFalse(TimerLaw.isRunning(payload))
        XCTAssertEqual(TimerLaw.elapsed(payload, now: now), 0)

        let running = TimerLaw.start(payload, now: now)
        XCTAssertTrue(TimerLaw.isRunning(running))
        XCTAssertEqual(running.startedAt, now)
        XCTAssertEqual(running.elapsed, 0)
        XCTAssertEqual(TimerLaw.elapsed(running, now: now.addingTimeInterval(90)), 90)
        XCTAssertEqual(TimerLaw.remaining(running, now: now.addingTimeInterval(90)), tenMinutes - 90)
    }

    func testPausingBanksTheRunAndResumingKeepsIt() {
        let running = TimerLaw.start(WidgetPayload(seconds: tenMinutes), now: now)
        let paused = TimerLaw.pause(running, now: now.addingTimeInterval(120))
        XCTAssertNil(paused.startedAt)
        XCTAssertEqual(paused.elapsed, 120)
        XCTAssertEqual(TimerLaw.elapsed(paused, now: now.addingTimeInterval(10_800)), 120)

        let resumed = TimerLaw.start(paused, now: now.addingTimeInterval(10_800))
        XCTAssertEqual(TimerLaw.elapsed(resumed, now: now.addingTimeInterval(10_860)), 180)
    }

    func testStartingARunningTimerDoesNotRestartIt() {
        let running = TimerLaw.start(WidgetPayload(seconds: tenMinutes), now: now)
        let again = TimerLaw.start(running, now: now.addingTimeInterval(200))
        XCTAssertEqual(again, running)
        XCTAssertEqual(TimerLaw.elapsed(again, now: now.addingTimeInterval(200)), 200)
    }

    func testPausingAStoppedTimerChangesNothing() {
        let payload = WidgetPayload(seconds: tenMinutes, elapsed: 45)
        XCTAssertEqual(TimerLaw.pause(payload, now: now), payload)
    }

    func testAClockThatMovedBackIsNotADebt() {
        let payload = WidgetPayload(seconds: tenMinutes, startedAt: now.addingTimeInterval(300))
        XCTAssertEqual(TimerLaw.elapsed(payload, now: now), 0)
        XCTAssertEqual(TimerLaw.remaining(payload, now: now), tenMinutes)
    }

    func testTheNamedLengthIsSpent() {
        let running = TimerLaw.start(WidgetPayload(seconds: tenMinutes), now: now)
        XCTAssertFalse(TimerLaw.isDone(running, now: now.addingTimeInterval(599)))
        XCTAssertTrue(TimerLaw.isDone(running, now: now.addingTimeInterval(600)))
        XCTAssertEqual(TimerLaw.remaining(running, now: now.addingTimeInterval(900)), 0)
    }

    func testATimerWithNoLengthIsNeverDone() {
        let running = TimerLaw.start(WidgetPayload(), now: now)
        XCTAssertFalse(TimerLaw.isDone(running, now: now.addingTimeInterval(86_400)))
    }

    func testTheLengthSurvivesAReset() {
        let spent = TimerLaw.pause(TimerLaw.start(WidgetPayload(seconds: tenMinutes), now: now), now: now.addingTimeInterval(300))
        let fresh = TimerLaw.reset(spent)
        XCTAssertEqual(fresh.seconds, tenMinutes)
        XCTAssertEqual(fresh.elapsed, 0)
        XCTAssertNil(fresh.startedAt)
    }

    func testTheFaceReadsAsMinutesAndSeconds() {
        XCTAssertEqual(TimerLaw.face(600), "10:00")
        XCTAssertEqual(TimerLaw.face(61), "1:01")
        XCTAssertEqual(TimerLaw.face(0), "0:00")
        XCTAssertEqual(TimerLaw.face(-5), "0:00")
    }

    /// `started_at` rides the wire in the desk's own date shape, and the whole
    /// payload must survive a round trip — a run lost in decoding is a run the
    /// person did that the desk forgot.
    func testARunSurvivesTheWire() throws {
        let running = TimerLaw.start(WidgetPayload(seconds: tenMinutes, elapsed: 30), now: now)
        let data = try FacioJSON.encoder.encode(running)
        XCTAssertTrue(String(data: data, encoding: .utf8)?.contains("started_at") == true)
        let decoded = try FacioJSON.decoder.decode(WidgetPayload.self, from: data)
        XCTAssertEqual(decoded, running)
        XCTAssertEqual(TimerLaw.elapsed(decoded, now: now.addingTimeInterval(60)), 90)
    }

    func testTheTimerCarriesItsOwnCellSizeAndIsOnTheLid() {
        XCTAssertEqual(TileCells.size(for: .compact).width, 2)
        XCTAssertTrue(WidgetType.timer.showsOnLid)
        // A timer may run on the tile itself (04).
        XCTAssertTrue(WidgetType.timer.tileRunsLive)
    }

    func testTheDoTimeCueReachesATimer() {
        let cues = [
            CueLaw.addCue(id: "meditation-cue", subjectId: "meditation", kind: .correction, text: "сядь ровно, дыши носом")
        ]
        let surfaced = CueLaw.surfaceCue(in: cues, subjectId: "meditation", widgetType: .timer)
        XCTAssertEqual(surfaced?.surface, .doTime)
    }
}
