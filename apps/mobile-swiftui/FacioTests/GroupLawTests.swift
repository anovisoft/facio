import XCTest
@testable import Facio

/// Mirror of `packages/domain/tests/test_groups.py`. A divergence here is a
/// release hole, not a nit.
final class GroupLawTests: XCTestCase {
    private let hours = [
        ClockTime(hour: 10, minute: 0),
        ClockTime(hour: 12, minute: 0),
        ClockTime(hour: 15, minute: 0),
        ClockTime(hour: 16, minute: 30),
        ClockTime(hour: 18, minute: 0),
        ClockTime(hour: 21, minute: 0),
        ClockTime(hour: 22, minute: 0),
    ]

    private var day: Date { FacioJSON.date(from: "2026-08-30T00:00:00") ?? Date() }

    private var group: String { GroupLaw.key(subjectId: "upwork", day: day) }

    private func at(_ clock: ClockTime) -> Date {
        ReminderClock.date(on: day, clock: clock)
    }

    private func check(_ index: Int, done: Bool = false, group: String?) -> Widget {
        Widget(
            id: "upwork-tick-\(index)",
            type: .tick,
            title: "проверить upwork",
            payload: WidgetPayload(done: done),
            status: done ? .done : .ready,
            when: at(hours[index]),
            section: .today,
            groupId: group,
            subjectId: "upwork",
            instanceId: "upwork-case-\(index)",
            tileSize: .compact
        )
    }

    private func kase(_ index: Int) -> Instance {
        Instance(
            id: "upwork-case-\(index)",
            subjectId: "upwork",
            when: at(hours[index]),
            status: .prepared
        )
    }

    private func seven(done: Set<Int> = []) -> ([Widget], [Instance]) {
        (
            (0..<hours.count).map { check($0, done: done.contains($0), group: group) },
            (0..<hours.count).map { kase($0) }
        )
    }

    func testTheKeyIsDerivedNotInvented() {
        XCTAssertEqual(GroupLaw.key(subjectId: "upwork", day: day), group)
        XCTAssertNotEqual(
            GroupLaw.key(subjectId: "upwork", day: at(ClockTime(hour: 23, minute: 59))),
            GroupLaw.key(subjectId: "gym", day: day)
        )
    }

    func testSevenChecksAreOneGroup() {
        let (widgets, cases) = seven()
        let face = GroupLaw.face(
            of: group,
            widgets: widgets,
            instances: cases,
            now: at(ClockTime(hour: 9, minute: 0))
        )
        XCTAssertEqual(face?.total, 7)
        XCTAssertEqual(face?.done, 0)
        XCTAssertEqual(face?.marks.compactMap(\.hour), hours)
        XCTAssertEqual(GroupLaw.members(of: group, in: widgets).count, 7)
    }

    func testAWidgetWithoutAGroupIsDrawnAlone() {
        // The old desk opens: no `group_id`, no group — one tile as before.
        let lone = check(0, group: nil)
        XCTAssertNil(GroupLaw.face(of: group, widgets: [lone], instances: [kase(0)], now: day))
        let cells = GroupLaw.cells([lone], instances: [kase(0)], now: day)
        XCTAssertEqual(cells.count, 1)
        if case .group = cells[0] { XCTFail("a widget with no group_id must draw alone") }
    }

    func testTheGroupDrawsOnceInThePlaceOfItsFirstMember() {
        let (widgets, cases) = seven()
        let other = Widget(
            id: "gym-counter",
            type: .counter,
            title: "gym",
            status: .ready,
            section: .today,
            subjectId: "gym",
            instanceId: "gym-open",
            tileSize: .compact
        )
        let cells = GroupLaw.cells([widgets[0], other] + widgets.dropFirst(), instances: cases, now: day)
        XCTAssertEqual(cells.map(\.id), ["g:\(group)", "w:gym-counter"])
    }

    func testAGroupOfOneIsATileOfOne() {
        let lone = check(0, group: group)
        let cells = GroupLaw.cells([lone], instances: [kase(0)], now: day)
        if case .group = cells[0] { XCTFail("one occurrence is one tile, not «1 / 1»") }
    }

    func testNextHourIsTheNearestOneStillAhead() {
        let (widgets, cases) = seven()
        let face = GroupLaw.face(
            of: group,
            widgets: widgets,
            instances: cases,
            now: at(ClockTime(hour: 15, minute: 40))
        )
        XCTAssertEqual(face?.nextHour, ClockTime(hour: 16, minute: 30))
    }

    /// The whole slice: marks are independent and unordered. Ticking 15:00
    /// closes 15:00; the 12:00 that was missed stays open and stays visible.
    func testALaterCheckDoesNotCloseAnEarlierMiss() {
        let (widgets, cases) = seven(done: [0, 2])
        let face = GroupLaw.face(
            of: group,
            widgets: widgets,
            instances: cases,
            now: at(ClockTime(hour: 15, minute: 40))
        )
        XCTAssertEqual(face?.done, 2)
        XCTAssertEqual(face?.total, 7)
        let open = face?.marks.filter { !$0.done }.compactMap(\.hour) ?? []
        XCTAssertTrue(open.contains(ClockTime(hour: 12, minute: 0)))
        XCTAssertFalse(open.contains(ClockTime(hour: 15, minute: 0)))
        XCTAssertEqual(face?.nextHour, ClockTime(hour: 16, minute: 30))
    }

    func testWhenEveryHourIsBehindTheFirstOpenOneIsShown() {
        let (widgets, cases) = seven(done: [0, 1])
        let face = GroupLaw.face(
            of: group,
            widgets: widgets,
            instances: cases,
            now: at(ClockTime(hour: 23, minute: 30))
        )
        XCTAssertEqual(face?.nextHour, ClockTime(hour: 15, minute: 0))
    }

    func testAFinishedGroupHasNoHourLeftToShow() {
        let (widgets, cases) = seven(done: Set(0..<7))
        let face = GroupLaw.face(
            of: group,
            widgets: widgets,
            instances: cases,
            now: at(ClockTime(hour: 23, minute: 30))
        )
        XCTAssertEqual(face?.done, 7)
        XCTAssertNil(face?.nextHour)
    }

    func testSkippedIsNotDone() {
        var widget = check(1, group: group)
        widget.status = .skipped
        widget.payload.done = false
        XCTAssertFalse(GroupLaw.isClosed(widget))
    }

    func testMarksAreOrderedByHourWhateverOrderTheyArriveIn() {
        let (widgets, cases) = seven()
        let shuffled = [widgets[4], widgets[0], widgets[6], widgets[2], widgets[1], widgets[5], widgets[3]]
        let face = GroupLaw.face(of: group, widgets: shuffled, instances: cases, now: day)
        XCTAssertEqual(face?.marks.compactMap(\.hour), hours)
    }

    func testALeadIsTheOccurrenceTheBigHourIsAbout() {
        let (widgets, cases) = seven(done: [0, 1])
        let face = GroupLaw.face(
            of: group,
            widgets: widgets,
            instances: cases,
            now: at(ClockTime(hour: 14, minute: 0))
        )
        XCTAssertEqual(face?.leadWidgetId, "upwork-tick-2")
    }

    /// A grouped case keeps the hour it is for; an ungrouped one is stamped now.
    func testClosingKeepsTheHourOfAGroupedCase() {
        let hour = at(hours[2])
        let now = at(ClockTime(hour: 15, minute: 42))
        XCTAssertEqual(GroupLaw.closingStamp(check(2, group: group), standing: hour, now: now), hour)
        XCTAssertEqual(GroupLaw.closingStamp(check(2, group: nil), standing: hour, now: now), now)
    }

    // MARK: - the reminder is an hour, not an occurrence

    private func alarm() -> (Widget, Instance) {
        let fireAt = at(hours[0])
        return (
            Widget(
                id: "upwork-reminder",
                type: .reminder,
                title: "проверить upwork",
                payload: WidgetPayload(fireAt: fireAt),
                status: .ready,
                when: fireAt,
                section: .today,
                subjectId: "upwork",
                instanceId: "upwork-open",
                tileSize: .wide
            ),
            Instance(id: "upwork-open", subjectId: "upwork", when: fireAt, status: .prepared)
        )
    }

    func testTheReminderCaseIsNotASlotOfTheCarousel() {
        let (widgets, cases) = seven()
        let (alarmWidget, alarmCase) = alarm()
        XCTAssertEqual(
            SlotLaw.hourInstanceIds(subjectId: "upwork", widgets: [alarmWidget] + widgets),
            ["upwork-open"]
        )
        let listed = SlotLaw.occurrenceInstances(
            subjectId: "upwork",
            instances: [alarmCase] + cases,
            widgets: [alarmWidget] + widgets
        )
        XCTAssertEqual(listed.map(\.id), cases.map(\.id))
    }

    func testAPracticeWhoseOnlyCaseIsItsAlarmKeepsIt() {
        // The bike: the alarm is the ride, and an empty carousel is worse.
        let (alarmWidget, alarmCase) = alarm()
        let listed = SlotLaw.occurrenceInstances(
            subjectId: "upwork",
            instances: [alarmCase],
            widgets: [alarmWidget]
        )
        XCTAssertEqual(listed.map(\.id), ["upwork-open"])
    }

    // MARK: - the caption under a slot

    func testASlotSaysItsHourOnlyWhenTheDayHoldsMoreThanOneCase() {
        let (_, cases) = seven()
        let caption = InstanceFaceLaw.slotCaption(cases[2], among: cases)
        XCTAssertTrue(caption.contains("15:00"), caption)
        let lone = [cases[2]]
        XCTAssertFalse(InstanceFaceLaw.slotCaption(cases[2], among: lone).contains("15:00"))
    }

    func testSevenSlotsOfOneDayAreAllDifferent() {
        let (_, cases) = seven()
        let captions = cases.map { InstanceFaceLaw.slotCaption($0, among: cases) }
        XCTAssertEqual(Set(captions).count, cases.count)
    }
}
