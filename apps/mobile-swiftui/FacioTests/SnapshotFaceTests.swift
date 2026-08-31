import XCTest
@testable import Facio

/// R14 part A. The centered chat card is drawn from what the service sent as
/// **state**, through this client's catalog — not from a sentence the service
/// wrote, and not from today's desk.
final class SnapshotFaceTests: XCTestCase {
    private func card(
        face: SnapshotFace?,
        line: String = "wire line",
        detail: String? = nil
    ) -> ChatSnapshot {
        ChatSnapshot(
            widgetId: "push-ups-counter",
            subjectId: "push-ups",
            instanceId: "push-ups-today",
            version: 3,
            title: "Отжимания",
            line: line,
            face: face,
            detail: detail
        )
    }

    // MARK: - The hole this closed

    func testPausedCardGoesThroughTheCatalogNotTheWire() throws {
        // The service used to send «на паузе» whatever `locale` said, while the
        // same phrase sat translated in `DisplayCopy`. The untranslated one won.
        let line = SnapshotFaceLaw.line(card(face: .paused, line: "на паузе"))
        XCTAssertEqual(line, DisplayCopy.pausedNow)
    }

    func testSkippedReminderIsOneStateNotAClockPlusAWord() throws {
        let line = SnapshotFaceLaw.line(
            card(face: .reminder(clock: ClockTime(hour: 19, minute: 0), closesAt: nil, skipped: true))
        )
        XCTAssertEqual(line, DisplayCopy.reminderSkipped)
    }

    // MARK: - Faces

    func testCounterDrawsCountAndGoal() throws {
        let line = SnapshotFaceLaw.line(card(face: .counter(count: 28, goal: 30)))
        XCTAssertEqual(line, DisplayCopy.counterFace(count: 28, goal: 30))
    }

    func testCounterWithoutAGoalStopsAfterTheNumber() throws {
        // « / 0» is a target nobody named — same rule as the tile and the slot.
        let line = SnapshotFaceLaw.line(card(face: .counter(count: 12, goal: nil)))
        XCTAssertEqual(line, DisplayCopy.counterFace(count: 12, goal: nil))
        XCTAssertFalse(line.contains("/"))
    }

    func testTickUsesTheSameTwoWordsAsEverywhereElse() throws {
        // The wire's own sentence says «не сделано»; the client has exactly one
        // phrase for that state and this is it.
        XCTAssertEqual(
            SnapshotFaceLaw.line(card(face: .tick(done: false), line: "не сделано")),
            DisplayCopy.tickState(done: false)
        )
        XCTAssertEqual(
            SnapshotFaceLaw.line(card(face: .tick(done: true), line: "готово")),
            DisplayCopy.tickState(done: true)
        )
    }

    func testChecklistAndStepperReadAsProgress() throws {
        XCTAssertEqual(
            SnapshotFaceLaw.line(card(face: .checklist(done: 1, total: 3))),
            DisplayCopy.counterFace(count: 1, goal: 3)
        )
        XCTAssertEqual(
            SnapshotFaceLaw.line(card(face: .stepper(step: 2, total: 3))),
            DisplayCopy.counterFace(count: 2, goal: 3)
        )
    }

    func testTimerIsAFrozenFaceNotARuntime() throws {
        XCTAssertEqual(SnapshotFaceLaw.line(card(face: .timer(seconds: 600))), TimerLaw.face(600))
    }

    func testReminderRebuildsTheDoorFromTheClock() throws {
        let line = SnapshotFaceLaw.line(
            card(
                face: .reminder(
                    clock: ClockTime(hour: 19, minute: 0),
                    closesAt: ClockTime(hour: 22, minute: 0),
                    skipped: false
                ),
                detail: "зал до 22"
            )
        )
        XCTAssertEqual(line, "19:00 · \(DisplayCopy.doorPhrase(ClockTime(hour: 22, minute: 0)))")
    }

    func testCueRidesUnderTheNumberInThePersonsOwnWords() throws {
        let line = SnapshotFaceLaw.line(
            card(face: .counter(count: 28, goal: 30), detail: "держи корпус и ягодицы")
        )
        XCTAssertEqual(line, "\(DisplayCopy.counterFace(count: 28, goal: 30)) · держи корпус и ягодицы")
    }

    // MARK: - The old wire

    func testACardWithoutAFaceKeepsItsLine() throws {
        // A service built before R14, or a card written into `talks.json`
        // before it. A sentence in the wrong language beats a blank card.
        XCTAssertEqual(SnapshotFaceLaw.line(card(face: nil, line: "28 / 30 · держи корпус")), "28 / 30 · держи корпус")
    }

    func testAnOlderCardDecodesWithNoFaceAtAll() throws {
        let json = Data(
            """
            {"widget_id":"w","subject_id":"push-ups","instance_id":"i","version":1,
             "title":"Отжимания","line":"на паузе"}
            """.utf8
        )
        let decoded = try JSONDecoder().decode(ChatSnapshot.self, from: json)
        XCTAssertNil(decoded.face)
        XCTAssertNil(decoded.detail)
        XCTAssertEqual(SnapshotFaceLaw.line(decoded), "на паузе")
    }

    func testAFaceKindThisBuildDoesNotKnowFallsBackInsteadOfThrowing() throws {
        let json = Data(
            """
            {"widget_id":"w","subject_id":"push-ups","instance_id":"i","version":1,
             "title":"Отжимания","line":"что-то новое","face":{"kind":"gauge","value":7}}
            """.utf8
        )
        let decoded = try JSONDecoder().decode(ChatSnapshot.self, from: json)
        XCTAssertEqual(decoded.face, .blank)
        XCTAssertEqual(SnapshotFaceLaw.line(decoded), "")
    }

    // MARK: - The picture is the snapshot's, not the desk's

    func testTheFaceComesOffTheCardAndNotOffTodaysWidget() throws {
        // 04: a snapshot is a picture of the moment it was written. The desk
        // moved on to 30; the card still says what it said.
        let stale = card(face: .counter(count: 28, goal: 30))
        XCTAssertEqual(SnapshotFaceLaw.face(stale.face!), .counter(count: 28, goal: 30))
        XCTAssertEqual(SnapshotFaceLaw.line(stale), DisplayCopy.counterFace(count: 28, goal: 30))
    }
}
