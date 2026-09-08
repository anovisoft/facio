import Foundation

/// Step 7 of the plan, and the only honest answer to «does the mechanic
/// work?».
///
/// The kill criteria were written down before anyone used this
/// (`docs/state/plan.md`): if in two weeks no cue was ever read at the moment
/// of doing, the mechanic does not work; if drift never surfaced before the
/// failure had already happened, the same. Numbers that arrive after the
/// TestFlight are numbers that arrive too late, so the arithmetic lives here
/// and the journal already carries everything it reads.
///
/// **This is a measurement of the product, not a score of the person** (P7).
/// Nothing here is a streak, nothing is drawn on a tile, and nothing feeds
/// back into what the lid asks for. It counts whether *we* built something
/// that lands — which is why «промахнулись» is a perfectly good result here
/// and a forbidden one on the lid.
///
/// Everything is derived from two things the device already has: the
/// append-only journal and the desk. No new field, no new store, and no number
/// kept in two places to drift apart.
enum MeasureLaw {
    /// Two weeks, because that is the window the kill criteria are written in.
    static let windowDays = 14

    /// Four weeks, because that is where «practices alive at week four» is.
    static let survivalDays = 28

    /// Doing, as opposed to reading. A day with one of these is a day the
    /// person actually used the thing; a day with only `cue_surfaced` on it is
    /// a day they opened the lid and looked.
    private static let doing: Set<JournalEventType> = [
        .instanceCompleted,
        .counterTicked,
        .tickToggled,
        .checklistItemToggled,
        .timerStarted,
        .stepperMoved,
        .talkTurn
    ]

    struct Report: Equatable, Sendable {
        var days: Int
        var cueSurfaced: Int
        var cueApplied: Int
        var driftShown: Int
        var driftAnswered: Int
        var driftRecovered: Int
        var talkTurns: Int
        var talkTurnsThatBuilt: Int
        var practicesReachingFourWeeks: Int
        var practicesAliveAtFourWeeks: Int
        var activeDays: Int

        /// 05: memory is measured by hit rate — surfaced **and** applied. `nil`
        /// while nothing has surfaced: zero out of zero is not a zero score,
        /// it is no measurement, and printing 0% there would read as failure.
        var cueHitRate: Double? {
            guard cueSurfaced > 0 else { return nil }
            return Double(cueApplied) / Double(cueSurfaced)
        }

        /// Q25: the share of turns that left mechanics behind. The complement
        /// is the number that decides whether this product ever needs a rule
        /// about what may be said to it — and the RFC's answer is «no limiter
        /// until the share grows», so the share has to exist first.
        var mechanicShare: Double? {
            guard talkTurns > 0 else { return nil }
            return Double(talkTurnsThatBuilt) / Double(talkTurns)
        }

        /// Of the drift cards shown, the ones the person took hold of. Answered
        /// or recovered — both are the ladder doing its job; neither is «tried
        /// harder», which is not on any card (never-do #21).
        var driftCaught: Int { min(driftShown, driftAnswered + driftRecovered) }
    }

    static func report(
        journal: [JournalEvent],
        desk: DeskSnapshot,
        now: Date,
        days: Int = windowDays
    ) -> Report {
        let calendar = SlotLaw.dayCalendar
        let start = calendar.date(byAdding: .day, value: -(days - 1), to: SlotLaw.startOfDay(for: now))
            ?? SlotLaw.startOfDay(for: now)
        let inWindow = journal.filter { $0.at >= start }

        let drift = inWindow.filter { $0.type == .driftSurfaced }
        let talk = inWindow.filter { $0.type == .talkTurn }
        let survival = fourWeekSurvival(desk: desk, now: now)

        return Report(
            days: days,
            cueSurfaced: inWindow.filter { $0.type == .cueSurfaced }.count,
            cueApplied: inWindow.filter { $0.type == .cueApplied }.count,
            driftShown: drift.count,
            driftAnswered: inWindow.filter { $0.type == .driftAnswered }.count,
            driftRecovered: drift.filter { recovered($0, desk: desk) }.count,
            talkTurns: talk.count,
            talkTurnsThatBuilt: talk.filter(built).count,
            practicesReachingFourWeeks: survival.reached,
            practicesAliveAtFourWeeks: survival.alive,
            activeDays: Set(
                inWindow
                    .filter { doing.contains($0.type) }
                    .map { SlotLaw.dayKey($0.at) }
            ).count
        )
    }

    /// A turn counts as built when it changed the desk or wrote a cue —
    /// mutate or remember, in Q25's words. Explaining a bound widget is the
    /// third thing Q25 names and it leaves no trace of its own, so it lands on
    /// the «only talked» side: the share is a floor, and a floor is the safe
    /// direction for a number that would justify a limiter.
    private static func built(_ event: JournalEvent) -> Bool {
        let payload = event.payload ?? [:]
        if payload["mutated"] == "true" { return true }
        return (Int(payload["cues"] ?? "0") ?? 0) > 0
    }

    /// Did the practice come back after the card? Anything the person did on it
    /// afterwards counts: a case closed, a case started. Read off the desk, not
    /// off the journal, so a run that began before the sync still shows.
    private static func recovered(_ event: JournalEvent, desk: DeskSnapshot) -> Bool {
        guard let subjectId = event.subjectId else { return false }
        return desk.instances.contains { instance in
            instance.subjectId == subjectId
                && instance.when > event.at
                && (instance.status == .completed || instance.status == .inProgress)
        }
    }

    /// How many practices got as far as four weeks, and how many of those are
    /// still standing.
    ///
    /// Birth is the **first case** of the practice, not a `created_at` field:
    /// the desk travels to the server and back, and a date this arithmetic
    /// alone would read has no business on that wire. Alive is the law's own
    /// answer, not a second definition — not retired, still carrying a rhythm,
    /// and not currently drifting.
    static func fourWeekSurvival(desk: DeskSnapshot, now: Date) -> (reached: Int, alive: Int) {
        let calendar = SlotLaw.dayCalendar
        guard let cutoff = calendar.date(byAdding: .day, value: -survivalDays, to: SlotLaw.startOfDay(for: now))
        else { return (0, 0) }
        var reached = 0
        var alive = 0
        for subject in desk.subjects {
            let born = desk.instances
                .filter { $0.subjectId == subject.id }
                .map(\.when)
                .min()
            guard let born, born <= cutoff else { continue }
            reached += 1
            if subject.status != .retired,
               !subject.cadence.isNone,
               !DriftLaw.isDrifting(subject, instances: desk.instances, now: now)
            {
                alive += 1
            }
        }
        return (reached, alive)
    }
}
