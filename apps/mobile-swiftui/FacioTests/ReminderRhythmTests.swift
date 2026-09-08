import XCTest
@testable import Facio

/// R20: the reminder rings from the rhythm, not from a stamp that stopped.
///
/// **What was measured before the repair.** A desk holding the founding bike
/// (`2×/week`, 19:00), created on day N and reopened on a later day — which is
/// exactly what `DeskStore.init` and the return to the foreground do on a
/// phone:
///
/// | day  | alarms | the widget's `fire_at` |
/// |------|--------|------------------------|
/// | N    | 1      | day N, 19:00           |
/// | N+1  | **0**  | day N, 19:00           |
/// | N+2  | **0**  | day N, 19:00           |
/// | N+7  | **0**  | day N, 19:00           |
///
/// The stamp never moved, because R19 rolled it forward for grouped practices
/// only. `alarms(from:now:)` took the day off that stamp, so every hour of the
/// window landed on a day already behind us and every one of them was dropped
/// as past. A grouped practice measured 7 on all four days — the roll-forward
/// was carrying it, and it alone.
///
/// The day now comes from `SlotLaw.dueDays` over the horizon the 7-day calendar
/// already builds (04: "fired from the subject's cadence and window"), so both
/// kinds ring and there is one count of days on the desk instead of two.
@MainActor
final class ReminderRhythmTests: XCTestCase {
    // MARK: - the hole that was measured

    func testALoneReminderStillRingsOnTheDaysAfterItWasMade() throws {
        for offset in [1, 2, 7] {
            let store = try openSeed(madeOn: day(0), on: day(offset))
            let today = bikeAlarms(store, on: day(offset))
            XCTAssertEqual(today.count, 1, "day N+\(offset)")
            XCTAssertEqual(
                ReminderClock.clock(from: try XCTUnwrap(today.first).fireAt),
                ClockTime(hour: 19, minute: 0),
                "day N+\(offset)"
            )
        }
    }

    /// The repair is not a second stamp-rewriter. `fire_at` is left exactly
    /// where it was written — a mark of the next fire (04) — and the ringing
    /// does not consult it for the day any more.
    func testTheStampIsNotRewrittenByAnybody() throws {
        let made = try openSeed(madeOn: day(0), on: day(0))
        let stamp = try XCTUnwrap(made.widget(id: "bike-reminder")?.reminderFireAt)
        XCTAssertTrue(SlotLaw.isSameDay(stamp, day(0)))

        for offset in [1, 2, 7] {
            let later = try openSeed(madeOn: day(0), on: day(offset))
            XCTAssertEqual(later.widget(id: "bike-reminder")?.reminderFireAt, stamp, "day N+\(offset)")
        }
    }

    // MARK: - the day is a conclusion from the rhythm

    func testADailyPracticeRingsOnEveryDayOfTheHorizon() throws {
        let snapshot = try practice(count: 1, period: .day, hours: [ClockTime(hour: 19, minute: 0)])
        let days = Set(
            ReminderScheduler.alarms(from: snapshot, now: day(0))
                .map { SlotLaw.startOfDay(for: $0.fireAt) }
        )
        XCTAssertEqual(days.count, ReminderScheduler.horizonDays)
    }

    /// `2×/week` is not `daily`. It rings on the days the law counts as owed,
    /// and the moment the week's count is met it goes quiet on its own —
    /// nothing was archived, postponed or marked done to silence it.
    ///
    /// Monday is the origin on purpose: the whole horizon then sits inside one
    /// ISO week, so what is measured is the count of that week and not the next
    /// week's fresh two.
    func testAWeeklyPracticeGoesQuietOnceItsCountIsMet() throws {
        let monday = day(1)
        var snapshot = try practice(count: 2, period: .week, hours: [ClockTime(hour: 19, minute: 0)])
        XCTAssertFalse(ReminderScheduler.alarms(from: snapshot, now: monday).isEmpty)

        let index = try XCTUnwrap(snapshot.instances.firstIndex { $0.id == "gym-open" })
        snapshot.instances[index].status = .completed
        snapshot.instances[index].when = ReminderClock.date(on: monday, clock: ClockTime(hour: 8, minute: 0))
        snapshot.instances.append(
            Instance(
                id: "gym-second",
                subjectId: "gym",
                when: ReminderClock.date(on: monday, clock: ClockTime(hour: 8, minute: 30)),
                status: .completed
            )
        )
        XCTAssertTrue(
            ReminderScheduler.alarms(from: snapshot, now: monday).isEmpty,
            "the week owes nothing more, so there is nothing to ring about"
        )
    }

    /// An hour set far ahead is the person's, not the rhythm's, and the horizon
    /// must not swallow it.
    func testAStampBeyondTheHorizonStillRings() throws {
        var snapshot = try practice(count: 1, period: .none, hours: [ClockTime(hour: 19, minute: 0)])
        let far = ReminderClock.date(on: day(20), clock: ClockTime(hour: 19, minute: 0))
        let index = try XCTUnwrap(snapshot.widgets.firstIndex { $0.id == "gym-reminder" })
        snapshot.widgets[index].payload.fireAt = far
        snapshot.widgets[index].when = far
        let caseIndex = try XCTUnwrap(snapshot.instances.firstIndex { $0.id == "gym-open" })
        snapshot.instances[caseIndex].when = far

        let alarms = ReminderScheduler.alarms(from: snapshot, now: day(0))
        XCTAssertEqual(alarms.count, 1)
        XCTAssertEqual(alarms.first?.fireAt, far)
    }

    // MARK: - the seed bike, which must not move

    func testTheSeedBikeRingsAtSevenOnTheDayItIsMadeWithTheIdItAlwaysHad() throws {
        let store = try openSeed(madeOn: day(0), on: day(0))
        let today = bikeAlarms(store, on: day(0))
        XCTAssertEqual(today.count, 1)
        let alarm = try XCTUnwrap(today.first)
        XCTAssertEqual(alarm.id, ReminderScheduler.alarmId(widgetId: "bike-reminder"))
        XCTAssertEqual(ReminderClock.clock(from: alarm.fireAt), ClockTime(hour: 19, minute: 0))
        XCTAssertTrue(alarm.body.contains("19:00"))
        XCTAssertTrue(alarm.body.contains("зал до 22"))
    }

    /// The R15 shape of an id is a lock: a pending request is cleared by the
    /// string it was added under. Today keeps the two spellings it had, and the
    /// day segment appears only on the days beyond today.
    func testTodaysIdsAreTheOnesTheyAlwaysWere() throws {
        let store = try openSeed(madeOn: day(0), on: day(0))
        let ids = ReminderScheduler.alarms(from: store.snapshot, now: day(0))
            .filter { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "bike-reminder")) }
            .map(\.id)
        XCTAssertTrue(ids.contains(ReminderScheduler.alarmId(widgetId: "bike-reminder")))
        XCTAssertTrue(ids.allSatisfy { $0 == ReminderScheduler.alarmId(widgetId: "bike-reminder") || $0.contains("#") })

        let hours = [ClockTime(hour: 10, minute: 0), ClockTime(hour: 19, minute: 0)]
        let snapshot = try practice(count: 1, period: .day, hours: hours)
        let many = ReminderScheduler.alarms(from: snapshot, now: day(0))
        XCTAssertTrue(
            many.contains { $0.id == ReminderScheduler.alarmId(widgetId: "gym-reminder", clock: hours[1]) }
        )
        // No two requests share an identifier — the second would overwrite the
        // first in the notification centre without a word.
        XCTAssertEqual(Set(many.map(\.id)).count, many.count)
    }

    // MARK: - the 64 the system keeps

    /// The heavy case Q34 came from: seven checks and seven hours, every day.
    func testSevenHoursDailyFitsInsideTheCeiling() throws {
        let snapshot = try practice(count: 7, period: .day, hours: sevenHours)
        let alarms = ReminderScheduler.alarms(from: snapshot, now: day(0))
        XCTAssertEqual(alarms.count, 7 * ReminderScheduler.horizonDays)
        XCTAssertEqual(alarms.count, 21)
        XCTAssertLessThan(alarms.count, 64)
    }

    /// A weekly practice with one hour is two or three requests, never a queue.
    func testAWeeklyPracticeIsAHandfulOfRequests() throws {
        let store = try openSeed(madeOn: day(0), on: day(0))
        let alarms = ReminderScheduler.alarms(from: store.snapshot, now: day(0))
        XCTAssertLessThanOrEqual(alarms.count, ReminderScheduler.horizonDays)
    }

    /// The ceiling is enforced here, where it can be reasoned about, and not
    /// discovered in the notification centre, where the overflow is silent and
    /// takes somebody else's alarm with it.
    func testTheQueueIsCutToTheBudgetNearestFirst() throws {
        var snapshot = try practice(count: 7, period: .day, hours: sevenHours)
        for extra in 1...3 {
            let more = try practice(count: 7, period: .day, hours: sevenHours, id: "gym-\(extra)")
            snapshot.subjects += more.subjects
            snapshot.instances += more.instances
            snapshot.widgets += more.widgets
        }
        let alarms = ReminderScheduler.alarms(from: snapshot, now: day(0))
        XCTAssertEqual(alarms.count, ReminderScheduler.alarmBudget)
        XCTAssertLessThanOrEqual(ReminderScheduler.alarmBudget, 64)
        // Nearest first: the far ones are rebuilt by the next enqueue anyway.
        XCTAssertEqual(alarms, alarms.sorted { $0.fireAt < $1.fireAt || ($0.fireAt == $1.fireAt && $0.id < $1.id) })
        XCTAssertEqual(Set(alarms.map(\.id)).count, alarms.count)
    }

    // MARK: - the silences are exactly the ones they were

    func testPausedRetiredArchivedSnoozedAndDoneAllStaySilent() throws {
        for status in [WidgetStatus.done, .snoozed, .archived] {
            var snapshot = try practice(count: 1, period: .day, hours: [ClockTime(hour: 19, minute: 0)])
            let index = try XCTUnwrap(snapshot.widgets.firstIndex { $0.id == "gym-reminder" })
            snapshot.widgets[index].status = status
            XCTAssertTrue(
                ReminderScheduler.alarms(from: snapshot, now: day(0)).isEmpty,
                "\(status) must not ring"
            )
        }
        for status in [SubjectStatus.retired, .paused] {
            var snapshot = try practice(count: 1, period: .day, hours: [ClockTime(hour: 19, minute: 0)])
            let index = try XCTUnwrap(snapshot.subjects.firstIndex { $0.id == "gym" })
            snapshot.subjects[index].status = status
            let alarms = ReminderScheduler.alarms(from: snapshot, now: day(0))
                .filter { $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "gym-reminder")) }
            XCTAssertTrue(alarms.isEmpty, "\(status) must not ring")
        }
    }

    // MARK: -

    private var sevenHours: [ClockTime] {
        [10, 12, 15, 18, 21, 22].map { ClockTime(hour: $0, minute: 0) }
            + [ClockTime(hour: 16, minute: 30)]
    }

    /// 2026-08-30 is a Sunday; 09:00 leaves every hour of the day still ahead.
    private func day(_ offset: Int) -> Date {
        let start = FacioJSON.date(from: "2026-08-30T09:00:00") ?? Date()
        return SlotLaw.dayCalendar.date(byAdding: .day, value: offset, to: start) ?? start
    }

    private func bikeAlarms(_ store: DeskStore, on when: Date) -> [ReminderAlarm] {
        ReminderScheduler.alarms(from: store.snapshot, now: when)
            .filter {
                $0.id.hasPrefix(ReminderScheduler.alarmId(widgetId: "bike-reminder"))
                    && SlotLaw.isSameDay($0.fireAt, when)
            }
    }

    /// A desk written on one day and opened on another — the phone's own path
    /// through `DeskStore.init`, with no wait and no rewritten clock.
    private func openSeed(madeOn made: Date, on when: Date) throws -> DeskStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-rhythm-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(try SeedFactory.buildSeed(now: made))
        return try DeskStore(repository: repository, now: { when })
    }

    private func practice(
        count: Int,
        period: CadencePeriod,
        hours: [ClockTime],
        id: String = "gym"
    ) throws -> DeskSnapshot {
        let window = TimeWindow(hours: hours)
        let fireAt = ReminderClock.reminderFireAt(window: window, on: day(0))
        let cadence = period == .none ? Cadence.noRhythm : try Cadence.of(count: count, period: period)
        return DeskSnapshot(
            subjects: [
                Subject(
                    id: id,
                    title: id,
                    cadence: cadence,
                    window: window,
                    instanceIds: ["\(id)-open"]
                ),
            ],
            cues: [],
            instances: [
                Instance(id: "\(id)-open", subjectId: id, when: fireAt, status: .prepared),
            ],
            widgets: [
                Widget(
                    id: "\(id)-reminder",
                    type: .reminder,
                    title: id,
                    payload: WidgetPayload(fireAt: fireAt),
                    status: .ready,
                    when: fireAt,
                    section: .today,
                    subjectId: id,
                    instanceId: "\(id)-open",
                    tileSize: .wide
                ),
            ]
        )
    }
}
