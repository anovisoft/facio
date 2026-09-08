import XCTest
@testable import Facio

/// R17 — one practice, one card. Mirror of the R17 half of
/// `packages/domain/tests/test_lid.py`. A divergence here is a release hole.
///
/// The phone showed one subject wearing two tiles that said the same thing: the
/// reminder («15:30» large, «18:00 22:00» small) and the group of the same day
/// («0/3», «15:30», the row of marks). The lid is a view of what is due now,
/// not a second inventory (P10), so the reminder is not drawn — and it is not
/// touched: it stays on the desk and keeps ringing.
final class LidReminderGroupTests: XCTestCase {
    private let hours = [
        ClockTime(hour: 15, minute: 30),
        ClockTime(hour: 18, minute: 0),
        ClockTime(hour: 22, minute: 0),
    ]

    private var now: Date { FacioJSON.date(from: "2026-08-15T09:00:00") ?? Date() }

    private func at(_ clock: ClockTime) -> Date {
        ReminderClock.date(on: now, clock: clock)
    }

    private var group: String { GroupLaw.key(subjectId: "upwork", day: now) }

    /// A practice promising `checks` a day with a reminder standing beside it.
    /// `stated` is what the person said (the window); `laid` is what actually
    /// landed on the cases. They differ exactly when R16 refused to guess which
    /// check happens when.
    private func upwork(
        stated: [ClockTime]? = nil,
        laid: [ClockTime]? = nil,
        group: String?? = nil,
        checks: Int = 3
    ) throws -> (Subject, [Instance], [Widget]) {
        let window = stated ?? hours
        let onCases = laid ?? window
        let stamp: String? = group ?? self.group
        let subject = Subject(
            id: "upwork",
            title: "посмотреть Upwork",
            cadence: try Cadence.of(count: checks, period: .day),
            window: TimeWindow(hours: window)
        )
        let cases = (0..<checks).map { index in
            Instance(
                id: "upwork-case-\(index)",
                subjectId: "upwork",
                when: at(onCases[index % onCases.count]),
                status: .prepared
            )
        }
        let ticks = cases.enumerated().map { index, kase in
            Widget(
                id: "upwork-tick-\(index)",
                type: .tick,
                title: "посмотреть Upwork",
                payload: WidgetPayload(done: false),
                status: .ready,
                when: kase.when,
                section: .today,
                groupId: stamp,
                subjectId: "upwork",
                instanceId: kase.id
            )
        }
        let alarm = Widget(
            id: "upwork-reminder",
            type: .reminder,
            title: "посмотреть Upwork",
            payload: WidgetPayload(fireAt: at(window[0])),
            status: .ready,
            when: at(window[0]),
            section: .today,
            subjectId: "upwork",
            instanceId: "upwork-hour"
        )
        let hourCase = Instance(
            id: "upwork-hour",
            subjectId: "upwork",
            when: at(window[0]),
            status: .prepared
        )
        return (subject, cases + [hourCase], ticks + [alarm])
    }

    private func todayIds(_ projection: LidProjection) -> [String] {
        projection.today.compactMap { item in
            if case .widget(_, let widget) = item { return widget.id }
            return nil
        }
    }

    func testGroupWithTheHoursHidesTheReminderTile() throws {
        let (subject, cases, widgets) = try upwork()
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertEqual(
            todayIds(projection),
            ["upwork-tick-0", "upwork-tick-1", "upwork-tick-2"]
        )
    }

    func testTheHiddenReminderIsGoneFromEverySection() throws {
        for section in [WidgetSection.today, .lifetime, .soon, .postponed] {
            let (subject, cases, widgets) = try upwork()
            let moved = widgets.map { widget -> Widget in
                guard widget.id == "upwork-reminder" else { return widget }
                var copy = widget
                copy.section = section
                return copy
            }
            let projection = LidProjectionLaw.project(
                now: now, subjects: [subject], instances: cases, widgets: moved
            )
            let drawn = Set(
                todayIds(projection)
                    + projection.lifetime.map(\.id)
                    + projection.soon.map(\.id)
                    + projection.postponed.map(\.id)
            )
            XCTAssertFalse(drawn.contains("upwork-reminder"), "\(section)")
        }
    }

    func testHidingTheTileDoesNotTouchTheDesk() throws {
        let (subject, cases, widgets) = try upwork()
        let before = widgets
        _ = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertEqual(widgets, before)
        let alarm = try XCTUnwrap(widgets.first { $0.id == "upwork-reminder" })
        XCTAssertEqual(alarm.status, .ready)
        XCTAssertNotEqual(alarm.status, .archived)
    }

    /// The load-bearing one. The scheduler reads the desk snapshot, never the
    /// lid projection, so a tile that is not drawn must ring exactly as before:
    /// same number of alarms, same hours, same ids.
    func testTheAlarmsAreTheSameWithTheTileHidden() throws {
        let (subject, cases, widgets) = try upwork()
        let snapshot = DeskSnapshot(
            subjects: [subject],
            cues: [],
            instances: cases,
            widgets: widgets
        )
        let alarms = ReminderScheduler.alarms(from: snapshot, now: now)
            .filter { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "upwork-reminder")) }
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertFalse(todayIds(projection).contains("upwork-reminder"))
        // Today's three hours, unchanged by the tile being hidden. The horizon
        // lays the same three on the next days too (R20), which is why this
        // counts today rather than the whole queue.
        let todayAlarms = alarms.filter { SlotLaw.isSameDay($0.fireAt, now) }
        XCTAssertEqual(todayAlarms.count, 3)
        XCTAssertEqual(todayAlarms.map { ReminderClock.clock(from: $0.fireAt) }.sorted(), hours)

        // The same desk with the group never stamped draws both tiles — and
        // rings the very same three alarms. Nothing about the pocket moved.
        let (loose, looseCases, looseWidgets) = try upwork(group: .some(nil))
        let looseSnapshot = DeskSnapshot(
            subjects: [loose],
            cues: [],
            instances: looseCases,
            widgets: looseWidgets
        )
        let looseAlarms = ReminderScheduler.alarms(from: looseSnapshot, now: now)
            .filter { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "upwork-reminder")) }
        XCTAssertEqual(looseAlarms.count, alarms.count)
        XCTAssertEqual(
            looseAlarms.map(\.id).sorted(),
            alarms.map(\.id).sorted()
        )
        XCTAssertEqual(
            looseAlarms.map(\.fireAt).sorted(),
            alarms.map(\.fireAt).sorted()
        )
    }

    func testAPracticeWithoutAGroupDrawsItsReminder() throws {
        let fixtureNow = try DomainFixtures.now()
        var bike = try XCTUnwrap(
            try DomainFixtures.widgets().first { $0.id == "bike-reminder" }
        )
        bike.section = .today
        let projection = LidProjectionLaw.project(
            now: fixtureNow,
            subjects: try DomainFixtures.subjects(),
            instances: [],
            widgets: [bike]
        )
        XCTAssertEqual(todayIds(projection), ["bike-reminder"])
    }

    func testFewerHoursThanChecksKeepsTheReminder() throws {
        let (subject, cases, widgets) = try upwork(laid: [ClockTime(hour: 9, minute: 0)])
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertTrue(todayIds(projection).contains("upwork-reminder"))
    }

    func testAGroupOfOneKeepsTheReminder() throws {
        let (subject, cases, widgets) = try upwork(stated: [hours[0]], checks: 1)
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertTrue(todayIds(projection).contains("upwork-reminder"))
    }

    func testAnUngroupedDeskKeepsTheReminder() throws {
        let (subject, cases, widgets) = try upwork(group: .some(nil))
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertTrue(todayIds(projection).contains("upwork-reminder"))
    }

    func testYesterdaysGroupDoesNotHideTodaysReminder() throws {
        let yesterday = try XCTUnwrap(FacioJSON.date(from: "2026-08-14T09:00:00"))
        let (subject, cases, widgets) = try upwork(
            group: .some(GroupLaw.key(subjectId: "upwork", day: yesterday))
        )
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertTrue(todayIds(projection).contains("upwork-reminder"))
    }

    func testAPracticeWithoutAWindowKeepsItsReminder() throws {
        var (subject, cases, widgets) = try upwork()
        subject.window = nil
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertTrue(todayIds(projection).contains("upwork-reminder"))
    }

    func testAPausedPracticeIsStillSilent() throws {
        var (subject, cases, widgets) = try upwork()
        subject = SubjectLaw.freeze(subject, now: now)
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: widgets
        )
        XCTAssertTrue(todayIds(projection).isEmpty)
    }

    func testAnArchivedReminderIsNotResurrectedByTheRule() throws {
        let (subject, cases, widgets) = try upwork()
        let archived = widgets.map { widget -> Widget in
            guard widget.id == "upwork-reminder" else { return widget }
            var copy = widget
            copy.status = .archived
            return copy
        }
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: archived
        )
        XCTAssertFalse(todayIds(projection).contains("upwork-reminder"))
    }

    /// 3/3 done is still one practice: the day is answered, not re-asked.
    func testAClosedGroupStillHidesTheReminder() throws {
        let (subject, cases, widgets) = try upwork()
        let closed = widgets.map { widget -> Widget in
            guard widget.type == .tick else { return widget }
            var copy = widget
            copy.status = .done
            copy.payload = WidgetPayload(done: true)
            return copy
        }
        let projection = LidProjectionLaw.project(
            now: now, subjects: [subject], instances: cases, widgets: closed
        )
        XCTAssertFalse(todayIds(projection).contains("upwork-reminder"))
    }

    // MARK: - the predicate itself

    func testAGroupCarryingTheStatedHoursSaysThemAll() throws {
        let (subject, cases, widgets) = try upwork()
        let face = try XCTUnwrap(
            GroupLaw.face(of: group, widgets: widgets, instances: cases, now: now)
        )
        XCTAssertTrue(GroupLaw.saysEveryHour(face, window: subject.window))
    }

    func testAGroupWhoseHoursNeverLandedSaysNothing() throws {
        let (subject, cases, widgets) = try upwork(laid: [ClockTime(hour: 9, minute: 0)])
        let face = try XCTUnwrap(
            GroupLaw.face(of: group, widgets: widgets, instances: cases, now: now)
        )
        XCTAssertFalse(GroupLaw.saysEveryHour(face, window: subject.window))
    }

    func testAPracticeWithoutAWindowStatesNoHourToRepeat() throws {
        let (_, cases, widgets) = try upwork()
        let face = try XCTUnwrap(
            GroupLaw.face(of: group, widgets: widgets, instances: cases, now: now)
        )
        XCTAssertFalse(GroupLaw.saysEveryHour(face, window: nil))
    }
}
