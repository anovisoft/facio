import XCTest
@testable import Facio

/// Mirror of `packages/domain/tests/test_drift.py`, on the same fixtures.
/// A divergence between the two ports is a release hole.
final class DriftLawTests: XCTestCase {
    private func silentBike(
        asksMade: Int = 0,
        retireRefusals: Int = 0
    ) throws -> (subject: Subject, instances: [Instance]) {
        var bike = try DomainFixtures.subject("bike")
        bike.driftAsksMade = asksMade
        bike.driftRetireRefusals = retireRefusals
        let last = try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00"))
        return (bike, [Instance(id: "old", subjectId: "bike", when: last, status: .completed)])
    }

    private func days(_ count: Int, after date: Date) -> Date {
        date.addingTimeInterval(TimeInterval(count) * 86_400)
    }

    func testBikeSilenceThresholds() throws {
        let bike = try DomainFixtures.subject("bike")
        let now = try DomainFixtures.now()
        for item in try DomainFixtures.scenarios().bikeSilence {
            let last = try XCTUnwrap(FacioJSON.date(from: item.lastCompleted))
            let instances = [Instance(id: "bike-\(item.lastCompleted)", subjectId: "bike", when: last, status: .completed)]
            XCTAssertEqual(DriftLaw.isDrifting(bike, instances: instances, now: now), item.expectDrifting, item.id)
        }
    }

    func testCadenceNoneWithoutInstancesIsNotDrift() throws {
        let oneOff = Subject(id: "gift", title: "one gift", cadence: try Cadence.none())
        XCTAssertFalse(DriftLaw.isDrifting(oneOff, instances: [], now: try DomainFixtures.now()))
    }

    func testNeverStartedSubjectIsNotDrift() throws {
        let bike = try DomainFixtures.subject("bike")
        XCTAssertFalse(DriftLaw.isDrifting(bike, instances: [], now: try DomainFixtures.now()))
    }

    func testMissTuesdayIsNotDrift() throws {
        let push = try DomainFixtures.subject("push-ups")
        let instances = try DomainFixtures.scenarios().missTuesday.instances
        XCTAssertFalse(DriftLaw.isDrifting(push, instances: instances, now: try DomainFixtures.now()))
    }

    func testRetiredSubjectIsNotDrifting() throws {
        var bike = try DomainFixtures.subject("bike")
        bike.status = .retired
        let last = try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00"))
        let instances = [Instance(id: "old", subjectId: "bike", when: last, status: .completed)]
        XCTAssertFalse(DriftLaw.isDrifting(bike, instances: instances, now: try DomainFixtures.now()))
    }

    func testPausedSubjectIsNotDrifting() throws {
        var bike = try DomainFixtures.subject("bike")
        let now = try DomainFixtures.now()
        bike.status = .paused
        bike.pausedAt = now
        let last = try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00"))
        let instances = [Instance(id: "old", subjectId: "bike", when: last, status: .completed)]
        XCTAssertFalse(DriftLaw.isDrifting(bike, instances: instances, now: now))
    }

    func testDriftCardPicksOldestSilence() throws {
        let bike = try DomainFixtures.subject("bike")
        let vegetables = try DomainFixtures.subject("vegetables")
        let now = try DomainFixtures.now()
        let instances = [
            Instance(id: "b", subjectId: "bike", when: try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00")), status: .completed),
            Instance(id: "v", subjectId: "vegetables", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-11T12:00:00")), status: .completed),
        ]
        let card = try XCTUnwrap(DriftLaw.driftCard(subjects: [bike, vegetables], instances: instances, now: now))
        XCTAssertEqual(card.subjectId, "bike")
        XCTAssertEqual(card.silentDays, 21)
        XCTAssertEqual(card.offer, .moveToToday)
    }

    // MARK: - Q28, the ladder

    func testLadderWalksTheSharedFixture() throws {
        for row in try DomainFixtures.scenarios().driftLadder {
            XCTAssertEqual(
                DriftLaw.nextOffer(asksMade: row.asksMade, retireRefusals: row.retireRefusals),
                row.expectOffer,
                row.id
            )
        }
    }

    func testLadderReadsOffTheSubject() throws {
        var bike = try DomainFixtures.subject("bike")
        XCTAssertEqual(DriftLaw.nextOffer(for: bike), .moveToToday)
        bike.driftAsksMade = 1
        XCTAssertEqual(DriftLaw.nextOffer(for: bike), .onceAWeek)
        bike.driftAsksMade = 2
        XCTAssertEqual(DriftLaw.nextOffer(for: bike), .retire)
        bike.driftRetireRefusals = 2
        XCTAssertEqual(DriftLaw.nextOffer(for: bike), .stop)
    }

    /// Every rung is less commitment than the one before it (never-do #21).
    func testLadderNeverClimbsBackUp() throws {
        var bike = try DomainFixtures.subject("bike")
        var rungs: [DriftOffer] = []
        for step in 0..<3 {
            bike.driftAsksMade = step
            rungs.append(DriftLaw.nextOffer(for: bike))
        }
        XCTAssertEqual(rungs, DriftOffer.ladder)
    }

    func testOneAskPerCadencePeriod() throws {
        var bike = try DomainFixtures.subject("bike")
        let now = try DomainFixtures.now()
        XCTAssertTrue(DriftLaw.canAskNow(bike, now: now))
        bike.driftAsksMade = 1
        bike.driftAskedAt = now
        XCTAssertFalse(DriftLaw.canAskNow(bike, now: now))
        XCTAssertFalse(DriftLaw.canAskNow(bike, now: days(7, after: now)))
        XCTAssertTrue(DriftLaw.canAskNow(bike, now: days(8, after: now)))
    }

    func testDailySubjectWaitsItsOwnShorterPeriod() throws {
        var vegetables = try DomainFixtures.subject("vegetables")
        let now = try DomainFixtures.now()
        vegetables.driftAsksMade = 1
        vegetables.driftAskedAt = now
        XCTAssertFalse(DriftLaw.canAskNow(vegetables, now: days(2, after: now)))
        XCTAssertTrue(DriftLaw.canAskNow(vegetables, now: days(3, after: now)))
    }

    func testTwoRefusalsAreEnoughToGoQuiet() throws {
        let (subject, instances) = try silentBike(asksMade: 2)
        let now = try DomainFixtures.now()
        XCTAssertEqual(DriftLaw.nextOffer(for: subject), .retire)

        let once = DriftLaw.refuse(subject, offer: .retire, now: now)
        XCTAssertEqual(once.driftRetireRefusals, 1)
        XCTAssertEqual(DriftLaw.nextOffer(for: once), .retire)

        let later = days(8, after: now)
        let twice = DriftLaw.refuse(once, offer: .retire, now: later)
        XCTAssertEqual(twice.driftRetireRefusals, 2)
        XCTAssertEqual(DriftLaw.nextOffer(for: twice), .stop)
        XCTAssertFalse(DriftLaw.canAskNow(twice, now: days(365, after: later)))
        // Alive in Deeds, without a rhythm. Nothing deleted, nothing hidden.
        XCTAssertEqual(twice.status, .active)
        XCTAssertTrue(twice.cadence.isNone)
        XCTAssertEqual(twice.cueIds, subject.cueIds)
        XCTAssertEqual(twice.instanceIds, subject.instanceIds)
        XCTAssertNil(DriftLaw.driftCard(subjects: [twice], instances: instances, now: days(30, after: later)))
    }

    func testRefusingALowerRungIsNotARetireRefusal() throws {
        let bike = try DomainFixtures.subject("bike")
        let refused = DriftLaw.refuse(bike, offer: .moveToToday, now: try DomainFixtures.now())
        XCTAssertEqual(refused.driftRetireRefusals, 0)
        XCTAssertEqual(refused.driftAsksMade, 1)
        XCTAssertEqual(DriftLaw.nextOffer(for: refused), .onceAWeek)
    }

    func testAnswerMoveToTodayChangesNoCommitment() throws {
        let bike = try DomainFixtures.subject("bike")
        let now = try DomainFixtures.now()
        let answered = DriftLaw.answer(bike, offer: .moveToToday, now: now)
        XCTAssertEqual(answered.cadence, bike.cadence)
        XCTAssertEqual(answered.status, bike.status)
        XCTAssertEqual(answered.driftAsksMade, 1)
        XCTAssertEqual(answered.driftAskedAt, now)
    }

    func testAnswerOnceAWeekShrinksTheRhythm() throws {
        let bike = try DomainFixtures.subject("bike")
        let answered = DriftLaw.answer(bike, offer: .onceAWeek, now: try DomainFixtures.now())
        XCTAssertEqual(answered.cadence.period, .week)
        XCTAssertEqual(answered.cadence.count, 1)
        XCTAssertEqual(answered.status, .shrunk)
    }

    func testAnswerRetireKeepsHistory() throws {
        let bike = try DomainFixtures.subject("bike")
        let answered = DriftLaw.answer(bike, offer: .retire, now: try DomainFixtures.now())
        XCTAssertEqual(answered.status, .retired)
        XCTAssertEqual(answered.cueIds, bike.cueIds)
        XCTAssertEqual(answered.instanceIds, bike.instanceIds)
    }

    func testAnsweringHidesTheCardUntilTheNextPeriod() throws {
        let (subject, instances) = try silentBike()
        let now = try DomainFixtures.now()
        let card = try XCTUnwrap(DriftLaw.driftCard(subjects: [subject], instances: instances, now: now))
        XCTAssertEqual(card.offer, .moveToToday)

        let answered = DriftLaw.answer(subject, offer: .moveToToday, now: now)
        XCTAssertNil(DriftLaw.driftCard(subjects: [answered], instances: instances, now: now))
        XCTAssertNil(DriftLaw.driftCard(subjects: [answered], instances: instances, now: days(7, after: now)))
        let next = try XCTUnwrap(
            DriftLaw.driftCard(subjects: [answered], instances: instances, now: days(8, after: now))
        )
        XCTAssertEqual(next.offer, .onceAWeek)
    }

    func testOneCardEvenWhenThreeSubjectsDrift() throws {
        let now = try DomainFixtures.now()
        let subjects = try ["bike", "push-ups", "vegetables"].map { try DomainFixtures.subject($0) }
        let instances = [
            Instance(id: "b", subjectId: "bike", when: try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00")), status: .completed),
            Instance(id: "p", subjectId: "push-ups", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-01T08:00:00")), status: .completed),
            Instance(id: "v", subjectId: "vegetables", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-05T12:00:00")), status: .completed),
        ]
        let card = try XCTUnwrap(DriftLaw.driftCard(subjects: subjects, instances: instances, now: now))
        XCTAssertEqual(card.subjectId, "bike")
    }

    /// Asked-this-period is filtered before the oldest wins, not after.
    func testAQuietSubjectDoesNotBlockTheOneBehindIt() throws {
        let now = try DomainFixtures.now()
        var bike = try DomainFixtures.subject("bike")
        bike.driftAsksMade = 1
        bike.driftAskedAt = now
        let push = try DomainFixtures.subject("push-ups")
        let instances = [
            Instance(id: "b", subjectId: "bike", when: try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00")), status: .completed),
            Instance(id: "p", subjectId: "push-ups", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-01T08:00:00")), status: .completed),
        ]
        let card = try XCTUnwrap(DriftLaw.driftCard(subjects: [bike, push], instances: instances, now: now))
        XCTAssertEqual(card.subjectId, "push-ups")
    }

    /// Pause is a boundary, not a rung: a frozen practice hears nothing.
    func testPausedSubjectIsNotAsked() throws {
        var (subject, instances) = try silentBike()
        let now = try DomainFixtures.now()
        subject.status = .paused
        subject.pausedAt = now
        XCTAssertNil(DriftLaw.driftCard(subjects: [subject], instances: instances, now: now))
    }

    func testStoppedSubjectNeverProducesACard() throws {
        var (subject, instances) = try silentBike(asksMade: 4, retireRefusals: 2)
        subject.driftAskedAt = nil
        XCTAssertNil(DriftLaw.driftCard(subjects: [subject], instances: instances, now: try DomainFixtures.now()))
    }

    func testPreparedInstanceDoesNotBreakSilence() throws {
        let bike = try DomainFixtures.subject("bike")
        let instances = [
            Instance(id: "old", subjectId: "bike", when: try XCTUnwrap(FacioJSON.date(from: "2026-07-25T18:00:00")), status: .completed),
            Instance(id: "prep", subjectId: "bike", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-20T19:00:00")), status: .prepared),
        ]
        XCTAssertTrue(DriftLaw.isDrifting(bike, instances: instances, now: try DomainFixtures.now()))
    }
}
