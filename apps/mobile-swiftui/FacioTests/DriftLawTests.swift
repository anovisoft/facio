import XCTest
@testable import Facio

final class DriftLawTests: XCTestCase {
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

    func testNextDriftOfferLadder() {
        XCTAssertEqual(DriftLaw.nextOffer(asksMade: 0, retireRefusals: 0), .moveToToday)
        XCTAssertEqual(DriftLaw.nextOffer(asksMade: 1, retireRefusals: 0), .onceAWeek)
        XCTAssertEqual(DriftLaw.nextOffer(asksMade: 2, retireRefusals: 0), .retire)
        XCTAssertEqual(DriftLaw.nextOffer(asksMade: 3, retireRefusals: 1), .retire)
        XCTAssertEqual(DriftLaw.nextOffer(asksMade: 4, retireRefusals: 2), .stop)
    }

    func testDriftCardUsesHistory() throws {
        let bike = try DomainFixtures.subject("bike")
        let last = try XCTUnwrap(FacioJSON.date(from: "2026-08-07T18:00:00"))
        let card = try XCTUnwrap(
            DriftLaw.driftCard(
                subjects: [bike],
                instances: [Instance(id: "b", subjectId: "bike", when: last, status: .completed)],
                now: try DomainFixtures.now(),
                histories: ["bike": DriftAskState(asksMade: 2, retireRefusals: 2)]
            )
        )
        XCTAssertEqual(card.offer, .stop)
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
