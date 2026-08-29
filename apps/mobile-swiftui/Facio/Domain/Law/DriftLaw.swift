import Foundation

/// Port of `packages/domain/facio_domain/drift.py`, 1:1 and driven by the same
/// fixtures. The law owns three decisions the model never makes (never-do AI
/// #10): whether a practice is drifting, which rung of the ladder is next, and
/// whether there is a right to speak at all.
enum DriftLaw {
    static let silenceDaysWeek = 8
    static let silenceDaysDay = 3

    /// Q28: two refusals of the offer to retire and the product goes quiet.
    static let retireRefusalsToSilence = 2

    private static let activity: Set<InstanceStatus> = [.completed, .inProgress]

    static func silenceThreshold(for cadence: Cadence) -> Int? {
        if cadence.isNone { return nil }
        switch cadence.period {
        case .week: return silenceDaysWeek
        case .day: return silenceDaysDay
        case .none: return nil
        }
    }

    /// How long the ladder waits between two asks about the same subject.
    /// Same arithmetic as the drift threshold on purpose: two numbers here
    /// would drift apart.
    static func askPeriodDays(for cadence: Cadence) -> Int? {
        silenceThreshold(for: cadence)
    }

    static func lastActivity(of subject: Subject, in instances: [Instance]) -> Date? {
        instances
            .filter { $0.subjectId == subject.id && activity.contains($0.status) }
            .map(\.when)
            .max()
    }

    static func silenceDays(of subject: Subject, in instances: [Instance], now: Date) -> Int? {
        guard let last = lastActivity(of: subject, in: instances) else { return nil }
        return calendarDays(from: last, to: now)
    }

    static func isDrifting(_ subject: Subject, instances: [Instance], now: Date) -> Bool {
        if subject.status == .retired || subject.status == .paused { return false }
        guard let threshold = silenceThreshold(for: subject.cadence) else { return false }
        guard let days = silenceDays(of: subject, in: instances, now: now) else { return false }
        return days >= threshold
    }

    /// The rungs, in order: move it to today, once a week instead, retire it.
    /// Each one is less commitment than the last. None of them is a bigger
    /// number and none of them is “try harder” (never-do #21).
    static func nextOffer(asksMade: Int, retireRefusals: Int) -> DriftOffer {
        if retireRefusals >= retireRefusalsToSilence { return .stop }
        if asksMade <= 0 { return .moveToToday }
        if asksMade == 1 { return .onceAWeek }
        return .retire
    }

    static func nextOffer(for subject: Subject) -> DriftOffer {
        nextOffer(asksMade: subject.driftAsksMade, retireRefusals: subject.driftRetireRefusals)
    }

    /// The right to speak: `stop` is silence forever, otherwise one ask per
    /// cadence period. Ignoring a card neither escalates inside the period nor
    /// silences the product after it (P8).
    static func canAskNow(_ subject: Subject, now: Date) -> Bool {
        if nextOffer(for: subject) == .stop { return false }
        guard let askedAt = subject.driftAskedAt else { return true }
        guard let period = askPeriodDays(for: subject.cadence) else { return false }
        return (calendarDays(from: askedAt, to: now) ?? 0) >= period
    }

    /// What the answer does to the practice. Down the ladder, never up.
    /// `moveToToday` changes no commitment — the widgets move, the promise
    /// stays. `retire` keeps every instance and every cue (04).
    static func answer(_ subject: Subject, offer: DriftOffer, now: Date) -> Subject {
        guard offer != .stop else { return subject }
        var next = subject
        next.driftAsksMade += 1
        next.driftAskedAt = now
        switch offer {
        case .moveToToday:
            break
        case .onceAWeek:
            next.cadence = Cadence.weekly(1)
            next.status = .shrunk
        case .retire:
            next.status = .retired
        case .stop:
            break
        }
        return next
    }

    /// “Not now”. Costs one rung; refusing to retire twice ends the asking and
    /// drops the cadence, so the practice stays in Deeds without a rhythm —
    /// alive, with its instances and cues, and never asked again (Q28).
    static func refuse(_ subject: Subject, offer: DriftOffer, now: Date) -> Subject {
        var next = subject
        next.driftAsksMade += 1
        next.driftAskedAt = now
        if offer == .retire {
            next.driftRetireRefusals += 1
        }
        if next.driftRetireRefusals >= retireRefusalsToSilence {
            next.cadence = Cadence.noRhythm
        }
        return next
    }

    /// At most one card. Subjects that may not be asked right now are filtered
    /// out first, so a quiet one does not block a louder failure behind it.
    static func driftCard(
        subjects: [Subject],
        instances: [Instance],
        now: Date
    ) -> DriftCard? {
        let drifting: [(days: Int, id: String, subject: Subject)] = subjects.compactMap { subject in
            guard isDrifting(subject, instances: instances, now: now),
                  canAskNow(subject, now: now),
                  let days = silenceDays(of: subject, in: instances, now: now)
            else { return nil }
            return (days, subject.id, subject)
        }
        guard let oldest = drifting.max(by: { lhs, rhs in
            if lhs.days != rhs.days { return lhs.days < rhs.days }
            return lhs.id < rhs.id
        }) else { return nil }
        return DriftCard(
            subjectId: oldest.subject.id,
            silentDays: oldest.days,
            offer: nextOffer(for: oldest.subject)
        )
    }

    private static func calendarDays(from start: Date, to end: Date) -> Int? {
        let calendar = Calendar.current
        return calendar.dateComponents(
            [.day],
            from: calendar.startOfDay(for: start),
            to: calendar.startOfDay(for: end)
        ).day
    }
}
