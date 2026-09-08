import XCTest
@testable import Facio

/// Step 7. The kill criteria were written down before anybody used this, and
/// they are all of the form «in two weeks, did X ever happen» — so every number
/// here has to be readable off what the device already keeps, and readable on
/// the day the question is asked, not after the TestFlight is over.
///
/// These are measurements of the product, never a score of the person (P7):
/// a bad number here is a good outcome for the test suite.
@MainActor
final class MeasureLawTests: XCTestCase {
    // MARK: - cue hit rate (05: surfaced + applied)

    func testTheHitRateIsAppliedOverSurfaced() {
        let report = MeasureLaw.report(
            journal: [
                event(.cueSurfaced, daysAgo: 3),
                event(.cueSurfaced, daysAgo: 2),
                event(.cueSurfaced, daysAgo: 1),
                event(.cueApplied, daysAgo: 1)
            ],
            desk: emptyDesk,
            now: now
        )
        XCTAssertEqual(report.cueSurfaced, 3)
        XCTAssertEqual(report.cueApplied, 1)
        XCTAssertEqual(try XCTUnwrap(report.cueHitRate), 1.0 / 3.0, accuracy: 0.0001)
    }

    /// Nothing surfaced is not a zero score, it is no measurement. Printing 0%
    /// there would read as «the cues failed» when nothing was ever shown.
    func testNothingSurfacedHasNoHitRateAtAll() {
        let report = MeasureLaw.report(journal: [], desk: emptyDesk, now: now)
        XCTAssertNil(report.cueHitRate)
        XCTAssertNil(report.mechanicShare)
    }

    func testTheWindowIsTwoWeeksAndOlderEventsAreOutsideIt() {
        let report = MeasureLaw.report(
            journal: [
                event(.cueSurfaced, daysAgo: 13),
                event(.cueSurfaced, daysAgo: 20)
            ],
            desk: emptyDesk,
            now: now
        )
        XCTAssertEqual(MeasureLaw.windowDays, 14)
        XCTAssertEqual(report.cueSurfaced, 1)
    }

    // MARK: - was the drift caught before the failure

    func testADriftCardThePersonAnsweredCountsAsCaught() {
        let report = MeasureLaw.report(
            journal: [
                event(.driftSurfaced, daysAgo: 5, subjectId: "bike"),
                event(.driftAnswered, daysAgo: 5, subjectId: "bike")
            ],
            desk: emptyDesk,
            now: now
        )
        XCTAssertEqual(report.driftShown, 1)
        XCTAssertEqual(report.driftAnswered, 1)
        XCTAssertEqual(report.driftCaught, 1)
    }

    /// The other way a card lands: nobody tapped anything, the person just went
    /// and did the thing. That is the mechanic working, and reading it off the
    /// desk is the only way to see it.
    func testAPracticeThatCameBackAfterTheCardCountsAsCaught() {
        var desk = emptyDesk
        desk.instances = [
            Instance(id: "bike-1", subjectId: "bike", when: daysAgo(2), status: .completed)
        ]
        let report = MeasureLaw.report(
            journal: [event(.driftSurfaced, daysAgo: 5, subjectId: "bike")],
            desk: desk,
            now: now
        )
        XCTAssertEqual(report.driftRecovered, 1)
        XCTAssertEqual(report.driftCaught, 1)
    }

    /// Activity that happened **before** the card is not a recovery — it is the
    /// activity whose absence produced the card in the first place.
    func testActivityBeforeTheCardIsNotARecovery() {
        var desk = emptyDesk
        desk.instances = [
            Instance(id: "bike-1", subjectId: "bike", when: daysAgo(9), status: .completed)
        ]
        let report = MeasureLaw.report(
            journal: [event(.driftSurfaced, daysAgo: 5, subjectId: "bike")],
            desk: desk,
            now: now
        )
        XCTAssertEqual(report.driftShown, 1)
        XCTAssertEqual(report.driftRecovered, 0)
        XCTAssertEqual(report.driftCaught, 0)
    }

    /// Answered **and** came back is one card caught, not two.
    func testCaughtNeverExceedsShown() {
        var desk = emptyDesk
        desk.instances = [
            Instance(id: "bike-1", subjectId: "bike", when: daysAgo(1), status: .completed)
        ]
        let report = MeasureLaw.report(
            journal: [
                event(.driftSurfaced, daysAgo: 5, subjectId: "bike"),
                event(.driftAnswered, daysAgo: 5, subjectId: "bike")
            ],
            desk: desk,
            now: now
        )
        XCTAssertEqual(report.driftCaught, 1)
    }

    // MARK: - Q25: the share of turns that left mechanics behind

    func testATurnThatChangedTheDeskCounts() {
        let report = MeasureLaw.report(
            journal: [
                talk(mutated: true, cues: 0, daysAgo: 1),
                talk(mutated: false, cues: 1, daysAgo: 1),
                talk(mutated: false, cues: 0, daysAgo: 1),
                talk(mutated: false, cues: 0, daysAgo: 1)
            ],
            desk: emptyDesk,
            now: now
        )
        XCTAssertEqual(report.talkTurns, 4)
        XCTAssertEqual(report.talkTurnsThatBuilt, 2)
        XCTAssertEqual(try XCTUnwrap(report.mechanicShare), 0.5, accuracy: 0.0001)
    }

    // MARK: - practices alive at week four

    func testAPracticeYoungerThanFourWeeksIsNotCountedEitherWay() throws {
        var desk = emptyDesk
        desk.subjects = [Subject(id: "bike", title: "bike", cadence: try Cadence.of(count: 1, period: .week))]
        desk.instances = [
            Instance(id: "bike-1", subjectId: "bike", when: daysAgo(10), status: .completed)
        ]
        let survival = MeasureLaw.fourWeekSurvival(desk: desk, now: now)
        XCTAssertEqual(survival.reached, 0)
        XCTAssertEqual(survival.alive, 0)
    }

    func testAPracticeStillRunningAtFourWeeksIsAlive() throws {
        var desk = emptyDesk
        desk.subjects = [Subject(id: "bike", title: "bike", cadence: try Cadence.of(count: 1, period: .week))]
        desk.instances = [
            Instance(id: "bike-old", subjectId: "bike", when: daysAgo(40), status: .completed),
            Instance(id: "bike-new", subjectId: "bike", when: daysAgo(2), status: .completed)
        ]
        let survival = MeasureLaw.fourWeekSurvival(desk: desk, now: now)
        XCTAssertEqual(survival.reached, 1)
        XCTAssertEqual(survival.alive, 1)
    }

    /// Reached four weeks and went quiet. It counts in the denominator and not
    /// in the numerator — which is the whole question step 7 is asking.
    func testAPracticeThatWentSilentReachedFourWeeksButIsNotAlive() throws {
        var desk = emptyDesk
        desk.subjects = [Subject(id: "bike", title: "bike", cadence: try Cadence.of(count: 1, period: .week))]
        desk.instances = [
            Instance(id: "bike-old", subjectId: "bike", when: daysAgo(40), status: .completed)
        ]
        let survival = MeasureLaw.fourWeekSurvival(desk: desk, now: now)
        XCTAssertEqual(survival.reached, 1)
        XCTAssertEqual(survival.alive, 0)
    }

    func testARetiredPracticeIsNotAlive() throws {
        var desk = emptyDesk
        desk.subjects = [
            Subject(
                id: "bike",
                title: "bike",
                cadence: try Cadence.of(count: 1, period: .week),
                status: .retired
            )
        ]
        desk.instances = [
            Instance(id: "bike-old", subjectId: "bike", when: daysAgo(40), status: .completed),
            Instance(id: "bike-new", subjectId: "bike", when: daysAgo(1), status: .completed)
        ]
        let survival = MeasureLaw.fourWeekSurvival(desk: desk, now: now)
        XCTAssertEqual(survival.reached, 1)
        XCTAssertEqual(survival.alive, 0)
    }

    // MARK: - active days

    /// The divisor of «cost per active day». Looking at the lid is not using
    /// it: a day with nothing but a cue surfacing on it is not an active day.
    func testActiveDaysCountDaysOfDoingAndNotDaysOfLooking() {
        let report = MeasureLaw.report(
            journal: [
                event(.cueSurfaced, daysAgo: 6),
                event(.instanceCompleted, daysAgo: 5),
                event(.counterTicked, daysAgo: 5),
                talk(mutated: false, cues: 0, daysAgo: 4)
            ],
            desk: emptyDesk,
            now: now
        )
        XCTAssertEqual(report.activeDays, 2)
    }

    // MARK: -

    private let now = FacioJSON.date(from: "2026-09-08T09:00:00") ?? Date()

    private var emptyDesk: DeskSnapshot {
        DeskSnapshot(subjects: [], cues: [], instances: [], widgets: [])
    }

    private func daysAgo(_ offset: Int) -> Date {
        SlotLaw.dayCalendar.date(byAdding: .day, value: -offset, to: now) ?? now
    }

    private func event(
        _ type: JournalEventType,
        daysAgo offset: Int,
        subjectId: String? = nil
    ) -> JournalEvent {
        JournalEvent(id: UUID().uuidString, type: type, at: daysAgo(offset), subjectId: subjectId)
    }

    private func talk(mutated: Bool, cues: Int, daysAgo offset: Int) -> JournalEvent {
        JournalEvent(
            id: UUID().uuidString,
            type: .talkTurn,
            at: daysAgo(offset),
            payload: ["mutated": mutated ? "true" : "false", "tools": "0", "cues": String(cues)]
        )
    }
}
