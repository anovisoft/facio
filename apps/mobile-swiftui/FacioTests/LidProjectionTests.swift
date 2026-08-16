import XCTest
@testable import Facio

final class LidProjectionTests: XCTestCase {
    func testEmptyTodayWithoutCommitmentsStaysEmpty() throws {
        let subjects = try DomainFixtures.subjects()
        let instances = try DomainFixtures.scenarios().emptyTodayNoCommitments.instances
        let projection = LidProjectionLaw.project(now: try DomainFixtures.now(), subjects: subjects, instances: instances, widgets: [])
        XCTAssertTrue(projection.today.isEmpty)
        XCTAssertNil(projection.driftCard)
    }

    func testEmptyTodayWithDriftShowsOneCard() throws {
        let subjects = try DomainFixtures.subjects()
        let instances = try DomainFixtures.scenarios().emptyTodayWithDrift.instances
        let projection = LidProjectionLaw.project(now: try DomainFixtures.now(), subjects: subjects, instances: instances, widgets: [])
        XCTAssertEqual(projection.driftCard?.subjectId, "bike")
        XCTAssertEqual(projection.today.count, 1)
        guard case .drift(let card) = projection.today[0] else {
            return XCTFail("expected drift")
        }
        XCTAssertEqual(card.subjectId, "bike")
        XCTAssertEqual(projection.today[0].kind, "drift")
        XCTAssertEqual(projection.today[0].band, .driftCard)
    }

    func testDoneWidgetTodayStaysInToday() throws {
        let now = try DomainFixtures.now()
        let widgets = [widget("done-set", status: .done, when: now)]
        let projection = LidProjectionLaw.project(now: now, subjects: try DomainFixtures.subjects(), instances: [], widgets: widgets)
        XCTAssertEqual(projection.today.count, 1)
        guard case .widget(let band, let item) = projection.today[0] else { return XCTFail("widget") }
        XCTAssertEqual(item.id, "done-set")
        XCTAssertEqual(band, .todayDone)
    }

    func testDoneWidgetOtherDayLeavesToday() throws {
        let yesterday = try XCTUnwrap(FacioJSON.date(from: "2026-08-14T12:00:00"))
        let widgets = [widget("old-set", status: .done, when: yesterday)]
        let projection = LidProjectionLaw.project(now: try DomainFixtures.now(), subjects: try DomainFixtures.subjects(), instances: [], widgets: widgets)
        XCTAssertTrue(projection.today.isEmpty)
    }

    func testLifetimeDoneTodayReturnsToToday() throws {
        let now = try DomainFixtures.now()
        let widgets = [widget("push-done", status: .done, when: now, section: .lifetime)]
        let projection = LidProjectionLaw.project(now: now, subjects: try DomainFixtures.subjects(), instances: [], widgets: widgets)
        XCTAssertEqual(projection.today.count, 1)
        guard case .widget(let band, let item) = projection.today[0] else { return XCTFail("widget") }
        XCTAssertEqual(band, .todayDone)
        XCTAssertEqual(item.id, "push-done")
        XCTAssertTrue(projection.lifetime.isEmpty)
    }

    func testRankV0Order() throws {
        let now = try DomainFixtures.now()
        let running = widget("running", status: .running, when: now)
        let overdue = widget("overdue", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-15T08:00:00")))
        let later = widget("later", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-15T18:00:00")))
        let incomplete = widget("incomplete")
        let done = widget("done-set", status: .done, when: now)
        let projection = LidProjectionLaw.project(
            now: now,
            subjects: try DomainFixtures.subjects(),
            instances: [],
            widgets: [later, incomplete, overdue, running, done]
        )
        let ids = projection.today.compactMap { item -> String? in
            if case .widget(_, let widget) = item { return widget.id }
            return nil
        }
        XCTAssertEqual(ids, ["running", "overdue", "later", "incomplete", "done-set"])
    }

    func testDriftCardRanksBetweenOverdueAndSoon() throws {
        let now = try DomainFixtures.now()
        let overdue = widget("overdue", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-15T08:00:00")))
        let later = widget("later", when: try XCTUnwrap(FacioJSON.date(from: "2026-08-15T18:00:00")))
        let projection = LidProjectionLaw.project(
            now: now,
            subjects: try DomainFixtures.subjects(),
            instances: try DomainFixtures.scenarios().emptyTodayWithDrift.instances,
            widgets: [later, overdue]
        )
        XCTAssertEqual(projection.today.map(\.kind), ["widget", "drift", "widget"])
    }

    func testSectionsPassThrough() throws {
        let projection = LidProjectionLaw.project(
            now: try DomainFixtures.now(),
            subjects: try DomainFixtures.subjects(),
            instances: [],
            widgets: try DomainFixtures.widgets()
        )
        XCTAssertEqual(Set(projection.lifetime.map(\.id)), ["push-ups-counter", "bike-reminder", "vegetables-tick"])
        XCTAssertTrue(projection.today.isEmpty)
    }

    private func widget(
        _ id: String,
        status: WidgetStatus = .ready,
        when: Date? = nil,
        section: WidgetSection = .today
    ) -> Widget {
        Widget(
            id: id,
            type: .counter,
            title: id,
            status: status,
            when: when,
            section: section,
            subjectId: "push-ups",
            instanceId: "\(id)-inst"
        )
    }
}
