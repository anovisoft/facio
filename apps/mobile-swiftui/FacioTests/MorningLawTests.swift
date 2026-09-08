import XCTest
@testable import Facio

/// Mirror of `packages/domain/tests/test_morning.py` on the same fixtures.
/// Q6: the morning card fires on a delta or on drift, and never on nothing.
final class MorningLawTests: XCTestCase {
    private func instance(_ subjectId: String, _ iso: String, status: InstanceStatus = .completed) throws -> Instance {
        Instance(
            id: "\(subjectId)-\(iso)",
            subjectId: subjectId,
            when: try XCTUnwrap(FacioJSON.date(from: iso)),
            status: status
        )
    }

    private func tile(
        _ subjectId: String,
        status: WidgetStatus = .ready,
        section: WidgetSection = .today
    ) -> Widget {
        Widget(
            id: "\(subjectId)-tile",
            type: .counter,
            title: subjectId,
            payload: WidgetPayload(),
            status: status,
            section: section,
            subjectId: subjectId,
            instanceId: "\(subjectId)-inst"
        )
    }

    func testPeriodLengthAndPromise() throws {
        let push = try DomainFixtures.subject("push-ups")
        let vegetables = try DomainFixtures.subject("vegetables")
        XCTAssertEqual(MorningLaw.periodDays(for: push.cadence), 7)
        XCTAssertEqual(MorningLaw.periodDays(for: vegetables.cadence), 1)
        XCTAssertNil(MorningLaw.periodDays(for: Cadence.noRhythm))
        XCTAssertEqual(MorningLaw.promised(for: push.cadence), 3)
        XCTAssertEqual(MorningLaw.promised(for: Cadence.noRhythm), 0)
    }

    func testDeltaIsPromisedMinusDone() throws {
        let push = try DomainFixtures.subject("push-ups")
        let now = try DomainFixtures.now()
        let instances = [
            try instance("push-ups", "2026-08-10T08:00:00"),
            try instance("push-ups", "2026-08-14T08:00:00"),
        ]
        XCTAssertEqual(MorningLaw.doneInPeriod(push, instances: instances, now: now), 2)
        XCTAssertEqual(MorningLaw.delta(push, instances: instances, now: now), 1)
    }

    /// A trailing period, so last month's sets do not pay this week's promise.
    func testWorkOutsideThePeriodDoesNotCount() throws {
        let push = try DomainFixtures.subject("push-ups")
        let old = [try instance("push-ups", "2026-07-20T08:00:00")]
        XCTAssertEqual(MorningLaw.doneInPeriod(push, instances: old, now: try DomainFixtures.now()), 0)
    }

    func testDoingMoreThanPromisedIsNotADebt() throws {
        let vegetables = try DomainFixtures.subject("vegetables")
        let instances = [
            try instance("vegetables", "2026-08-15T09:00:00"),
            try instance("vegetables", "2026-08-15T19:00:00"),
        ]
        XCTAssertEqual(MorningLaw.delta(vegetables, instances: instances, now: try DomainFixtures.now()), 0)
    }

    func testEmptyDayWithoutDeltaOrDriftStaysEmpty() throws {
        let scenario = try DomainFixtures.scenarios().emptyTodayNoCommitments
        let projection = LidProjectionLaw.project(
            now: try DomainFixtures.now(),
            subjects: try DomainFixtures.subjects(),
            instances: scenario.instances,
            widgets: []
        )
        XCTAssertTrue(projection.today.isEmpty)
        XCTAssertNil(projection.driftCard)
        XCTAssertNil(projection.deltaCard)
    }

    func testDeltaAlonePutsOneCalmCardOnToday() throws {
        let scenario = try DomainFixtures.scenarios().emptyTodayWithDelta
        let projection = LidProjectionLaw.project(
            now: try DomainFixtures.now(),
            subjects: try DomainFixtures.subjects(),
            instances: scenario.instances,
            widgets: []
        )
        XCTAssertNil(projection.driftCard)
        let card = try XCTUnwrap(projection.deltaCard)
        XCTAssertEqual(card.subjectId, scenario.expectDeltaSubject)
        XCTAssertEqual(card.promised, scenario.expectDeltaPromised)
        XCTAssertEqual(card.done, scenario.expectDeltaDone)
        XCTAssertEqual(card.remaining, scenario.expectDeltaRemaining)
        XCTAssertEqual(projection.today.map(\.kind), ["delta"])
    }

    func testDriftBeatsDeltaSoTheMorningSaysOneThing() throws {
        let scenario = try DomainFixtures.scenarios().emptyTodayWithDrift
        let projection = LidProjectionLaw.project(
            now: try DomainFixtures.now(),
            subjects: try DomainFixtures.subjects(),
            instances: scenario.instances,
            widgets: []
        )
        XCTAssertNotNil(projection.driftCard)
        XCTAssertNil(projection.deltaCard)
        XCTAssertEqual(projection.today.map(\.kind), ["drift"])
    }

    func testAPracticeThatNeverRanOwesNothing() throws {
        XCTAssertNil(
            MorningLaw.deltaCard(
                subjects: try DomainFixtures.subjects(),
                instances: [],
                widgets: [],
                now: try DomainFixtures.now()
            )
        )
    }

    func testATileAlreadyOnTodayIsTheDelta() throws {
        let push = try DomainFixtures.subject("push-ups")
        let now = try DomainFixtures.now()
        let instances = [try instance("push-ups", "2026-08-14T08:00:00")]
        XCTAssertNotNil(MorningLaw.deltaCard(subjects: [push], instances: instances, widgets: [], now: now))
        XCTAssertNil(
            MorningLaw.deltaCard(
                subjects: [push],
                instances: instances,
                widgets: [tile("push-ups")],
                now: now
            )
        )
    }

    func testADoneTileDoesNotCancelTheRestOfTheWeek() throws {
        let push = try DomainFixtures.subject("push-ups")
        let instances = [try instance("push-ups", "2026-08-14T08:00:00")]
        let card = try XCTUnwrap(
            MorningLaw.deltaCard(
                subjects: [push],
                instances: instances,
                widgets: [tile("push-ups", status: .done)],
                now: try DomainFixtures.now()
            )
        )
        XCTAssertEqual(card.remaining, 2)
    }

    func testPausedAndRetiredPracticesOweNothing() throws {
        var push = try DomainFixtures.subject("push-ups")
        let instances = [try instance("push-ups", "2026-08-14T08:00:00")]
        for status in [SubjectStatus.paused, .retired] {
            push.status = status
            XCTAssertNil(
                MorningLaw.deltaCard(
                    subjects: [push],
                    instances: instances,
                    widgets: [],
                    now: try DomainFixtures.now()
                ),
                "\(status)"
            )
        }
    }

    func testBiggestShortfallWinsWhenTwoPracticesAreBehind() throws {
        let push = try DomainFixtures.subject("push-ups")
        let bike = try DomainFixtures.subject("bike")
        let instances = [
            try instance("push-ups", "2026-08-14T08:00:00"),
            try instance("bike", "2026-08-13T18:00:00"),
        ]
        let card = try XCTUnwrap(
            MorningLaw.deltaCard(
                subjects: [push, bike],
                instances: instances,
                widgets: [],
                now: try DomainFixtures.now()
            )
        )
        XCTAssertEqual(card.subjectId, "push-ups")
        XCTAssertEqual(card.remaining, 2)
    }

    // MARK: - R19 reaches the morning too

    /// A tile the lid refuses to draw must not answer for today.
    ///
    /// R19 stopped a closed day's checks from being **drawn**; the morning kept
    /// counting them. Seven `ready` tiles in the `today` section made
    /// `hasLiveTileToday` say the practice was already asking, and the delta
    /// line was swallowed — so the second morning had neither a tile nor a
    /// line, with «7 обещано, 0 сделано» computed and thrown away.
    func testYesterdaysGroupDoesNotSilenceTodaysDelta() throws {
        let hours = [10, 12, 15, 18, 21, 22].map { ClockTime(hour: $0, minute: 0) }
            + [ClockTime(hour: 16, minute: 30)]
        let yesterday = try XCTUnwrap(FacioJSON.date(from: "2026-09-07T00:00:00"))
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-09-08T09:00:00"))
        let subject = Subject(
            id: "upwork",
            title: "проверить upwork",
            cadence: try Cadence.of(count: hours.count, period: .day),
            window: TimeWindow(hours: hours)
        )
        var widgets: [Widget] = []
        var instances: [Instance] = []
        for (index, hour) in hours.sorted().enumerated() {
            let closed = index < 3
            let when = ReminderClock.date(on: yesterday, clock: hour)
            widgets.append(
                Widget(
                    id: "upwork-tick-\(index)",
                    type: .tick,
                    title: "проверить upwork",
                    payload: WidgetPayload(done: closed),
                    status: closed ? .done : .ready,
                    when: when,
                    section: .today,
                    groupId: GroupLaw.key(subjectId: "upwork", day: yesterday),
                    subjectId: "upwork",
                    instanceId: "upwork-case-\(index)",
                    tileSize: .compact
                )
            )
            instances.append(
                Instance(
                    id: "upwork-case-\(index)",
                    subjectId: "upwork",
                    when: when,
                    status: closed ? .completed : .prepared
                )
            )
        }

        let projection = LidProjectionLaw.project(
            now: now,
            subjects: [subject],
            instances: instances,
            widgets: widgets
        )
        // Nothing of yesterday is drawn — that is R19, and it stays true.
        XCTAssertTrue(projection.today.allSatisfy { item in
            if case .widget = item { return false }
            return true
        })
        XCTAssertEqual(MorningLaw.delta(subject, instances: instances, now: now), hours.count)
        let card = try XCTUnwrap(
            MorningLaw.deltaCard(subjects: [subject], instances: instances, widgets: widgets, now: now)
        )
        XCTAssertEqual(card.subjectId, "upwork")
        XCTAssertEqual(card.remaining, hours.count)
    }
}
