import XCTest
@testable import Facio

@MainActor
final class InstanceLawTests: XCTestCase {
    func testShouldCloneWhenTodayReady() {
        XCTAssertTrue(InstanceLaw.shouldClone(template: widget(section: .today, status: .ready), now: now))
    }

    func testShouldCloneWhenRunning() {
        XCTAssertTrue(InstanceLaw.shouldClone(template: widget(section: .lifetime, status: .running), now: now))
    }

    func testShouldCloneWhenDoneToday() {
        var done = widget(section: .today, status: .done)
        done.when = now
        XCTAssertTrue(InstanceLaw.shouldClone(template: done, now: now))
    }

    func testShouldRebindLifetimeReady() {
        XCTAssertFalse(InstanceLaw.shouldClone(template: widget(section: .lifetime, status: .ready), now: now))
    }

    func testShouldRebindOldDone() {
        var done = widget(section: .lifetime, status: .done)
        done.when = now.addingTimeInterval(-86_400)
        XCTAssertFalse(InstanceLaw.shouldClone(template: done, now: now))
    }

    func testPreferredLivePicksTodayReadyFirst() {
        let today = widget(section: .today, status: .ready)
        let lifetime = widget(section: .lifetime, status: .ready)
        var lifetimeAlt = lifetime
        lifetimeAlt.id = "other"
        lifetimeAlt.instanceId = "other"
        let picked = InstanceLaw.preferredLive(in: [lifetimeAlt, today], subjectId: "push-ups", now: now)
        XCTAssertEqual(picked?.id, today.id)
    }

    func testPreferredLiveFallsBackToDoneToday() {
        var done = widget(section: .today, status: .done)
        done.when = now
        let picked = InstanceLaw.preferredLive(in: [done], subjectId: "push-ups", now: now)
        XCTAssertEqual(picked?.id, done.id)
    }

    func testResetCounterStartsAtZero() {
        let payload = InstanceLaw.resetPayload(of: widget(section: .today, status: .ready), now: now, window: nil)
        XCTAssertEqual(payload.count, 0)
        XCTAssertEqual(payload.target, 30)
    }

    private var now: Date {
        FacioJSON.date(from: "2026-08-16T12:00:00")!
    }

    private func widget(section: WidgetSection, status: WidgetStatus) -> Widget {
        Widget(
            id: "push-ups-counter",
            type: .counter,
            title: "push-ups",
            payload: WidgetPayload(count: 28, target: 30),
            status: status,
            section: section,
            subjectId: "push-ups",
            instanceId: "push-ups-open",
            tileSize: .compact
        )
    }
}
