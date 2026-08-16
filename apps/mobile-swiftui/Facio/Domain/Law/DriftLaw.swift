import Foundation

enum DriftLaw {
    static let silenceDaysWeek = 8
    static let silenceDaysDay = 3

    private static let activity: Set<InstanceStatus> = [.completed, .inProgress]

    static func silenceThreshold(for cadence: Cadence) -> Int? {
        if cadence.isNone { return nil }
        switch cadence.period {
        case .week: return silenceDaysWeek
        case .day: return silenceDaysDay
        case .none: return nil
        }
    }

    static func lastActivity(of subject: Subject, in instances: [Instance]) -> Date? {
        instances
            .filter { $0.subjectId == subject.id && activity.contains($0.status) }
            .map(\.when)
            .max()
    }

    static func silenceDays(of subject: Subject, in instances: [Instance], now: Date) -> Int? {
        guard let last = lastActivity(of: subject, in: instances) else { return nil }
        let calendar = Calendar.current
        return calendar.dateComponents([.day], from: calendar.startOfDay(for: last), to: calendar.startOfDay(for: now)).day
    }

    static func isDrifting(_ subject: Subject, instances: [Instance], now: Date) -> Bool {
        if subject.status == .retired { return false }
        guard let threshold = silenceThreshold(for: subject.cadence) else { return false }
        guard let days = silenceDays(of: subject, in: instances, now: now) else { return false }
        return days >= threshold
    }

    static func nextOffer(asksMade: Int, retireRefusals: Int) -> DriftOffer {
        if retireRefusals >= 2 { return .stop }
        if asksMade <= 0 { return .moveToToday }
        if asksMade == 1 { return .onceAWeek }
        return .retire
    }

    static func driftCard(
        subjects: [Subject],
        instances: [Instance],
        now: Date,
        histories: [String: DriftAskState] = [:]
    ) -> DriftCard? {
        let drifting: [(days: Int, id: String, subject: Subject)] = subjects.compactMap { subject in
            guard isDrifting(subject, instances: instances, now: now),
                  let days = silenceDays(of: subject, in: instances, now: now)
            else { return nil }
            return (days, subject.id, subject)
        }
        guard let oldest = drifting.max(by: { lhs, rhs in
            if lhs.days != rhs.days { return lhs.days < rhs.days }
            return lhs.id < rhs.id
        }) else { return nil }
        let state = histories[oldest.subject.id] ?? DriftAskState()
        return DriftCard(
            subjectId: oldest.subject.id,
            silentDays: oldest.days,
            offer: nextOffer(asksMade: state.asksMade, retireRefusals: state.retireRefusals)
        )
    }
}
