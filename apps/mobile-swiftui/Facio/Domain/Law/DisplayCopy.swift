import Foundation

enum DisplayCopy {
    static func title(subjectId: String, stored: String) -> String {
        switch subjectId {
        case "push-ups": String(localized: "Отжимания", comment: "Subject title for push-ups")
        case "vegetables": String(localized: "Овощи", comment: "Subject title for vegetables")
        case "bike": String(localized: "Велосипед", comment: "Subject title for the exercise bike")
        default: stored
        }
    }

    /// Counter face on Inspect, and the shape the lid tile paints in two fonts.
    /// No goal — no goal drawn: «0 / 0» is a target nobody named.
    static func counterFace(count: Int, goal: Int?) -> String {
        guard let goal else {
            return String(localized: "\(count)", comment: "Counter face without a goal")
        }
        return String(localized: "\(count) / \(goal)", comment: "Counter face: count and goal")
    }

    /// What VoiceOver reads off a counter tile. Without a goal it says the
    /// number and stops, the same way the tile does.
    static func counterAccessibility(title: String, count: Int, goal: Int?, cue: String?) -> String {
        switch (goal, cue) {
        case (.some(let goal), .some(let cue)):
            String(
                localized: "\(title), \(count) из \(goal), \(cue)",
                comment: "Counter tile accessibility: title, count of target, cue"
            )
        case (.some(let goal), .none):
            String(
                localized: "\(title), \(count) из \(goal)",
                comment: "Counter tile accessibility: title, count of target"
            )
        case (.none, .some(let cue)):
            String(
                localized: "\(title), \(count), \(cue)",
                comment: "Counter tile accessibility without a goal: title, count, cue"
            )
        case (.none, .none):
            String(
                localized: "\(title), \(count)",
                comment: "Counter tile accessibility without a goal: title, count"
            )
        }
    }

    static var pauseCheckInBody: String {
        String(localized: "готов тренироваться?", comment: "Pause check-in reminder body")
    }

    static var pausedNow: String {
        String(localized: "на паузе", comment: "Paused practice is not due today")
    }

    static func succeedBy(_ window: TimeWindow) -> String {
        String(localized: "успеть к \(window.latestBy.shortLabel)", comment: "Reminder window deadline")
    }

    static func silencePhrase(_ days: Int) -> String {
        switch days {
        case 21:
            String(localized: "три недели", comment: "Drift silence, three weeks")
        case 14:
            String(localized: "две недели", comment: "Drift silence, two weeks")
        case 7:
            String(localized: "неделю", comment: "Drift silence, one week")
        default:
            String(localized: "\(days) дней", comment: "Drift silence in days")
        }
    }

    static func driftLine(subjectId: String, stored: String, silentDays: Int) -> String {
        let name = title(subjectId: subjectId, stored: stored)
        let silence = silencePhrase(silentDays)
        return String(localized: "\(name) — не было \(silence). Сделать меньше?", comment: "Drift card body")
    }

    static func driftChip(_ offer: DriftOffer) -> String {
        switch offer {
        case .moveToToday:
            String(localized: "сегодня", comment: "Drift chip: move to today")
        case .onceAWeek:
            String(localized: "раз в неделю", comment: "Drift chip: once a week")
        case .retire:
            String(localized: "убрать", comment: "Drift chip: retire")
        case .stop:
            String(localized: "убрать", comment: "Drift chip unused stop")
        }
    }

    /// Saying no to the rung on offer. Not a dismissal of the practice: the
    /// card comes back a rung lower after a full cadence period, and after two
    /// refusals of «убрать» it does not come back at all (Q28).
    static var driftRefuse: String {
        String(localized: "не сейчас", comment: "Drift chip: refuse this rung")
    }

    /// The calm morning line (Q6). A count, not a verdict: no streak, no
    /// «you are behind», nothing to answer.
    static func deltaLine(
        subjectId: String,
        stored: String,
        remaining: Int,
        promised: Int,
        period: CadencePeriod
    ) -> String {
        let name = title(subjectId: subjectId, stored: stored)
        switch period {
        case .day:
            return String(
                localized: "\(name) — осталось \(remaining) из \(promised) сегодня",
                comment: "Delta card body for a daily rhythm"
            )
        case .week, .none:
            return String(
                localized: "\(name) — осталось \(remaining) из \(promised) на этой неделе",
                comment: "Delta card body for a weekly rhythm"
            )
        }
    }

    static func cadence(_ cadence: Cadence) -> String {
        if cadence.isNone {
            return String(localized: "без ритма", comment: "Cadence none")
        }
        let count = cadence.count ?? 0
        switch cadence.period {
        case .day:
            if count == 1 {
                return String(localized: "каждый день", comment: "Cadence 1/day")
            }
            return String(localized: "\(count)× в день", comment: "Cadence n/day")
        case .week:
            if count == 1 {
                return String(localized: "раз в неделю", comment: "Cadence 1/week")
            }
            return String(localized: "\(count)× в неделю", comment: "Cadence n/week")
        case .none:
            return String(localized: "без ритма", comment: "Cadence none")
        }
    }

    static func holding(
        subject: Subject,
        instances: [Instance],
        now: Date,
        liveSection: WidgetSection?,
        liveStatus: WidgetStatus?
    ) -> String {
        if subject.status == .retired {
            return String(localized: "убрана", comment: "Deed holding: retired")
        }
        if subject.status == .paused {
            return String(localized: "на паузе", comment: "Deed holding: paused")
        }
        if DriftLaw.isDrifting(subject, instances: instances, now: now),
           let days = DriftLaw.silenceDays(of: subject, in: instances, now: now)
        {
            return String(localized: "не было \(silencePhrase(days))", comment: "Deed holding: drift")
        }
        if liveStatus == .done, liveSection == .today {
            return String(localized: "готово сегодня", comment: "Deed holding: done today")
        }
        if liveSection == .today {
            return String(localized: "на Сегодня", comment: "Deed holding: on today")
        }
        if liveSection == .lifetime {
            return String(localized: "под рукой", comment: "Deed holding: lifetime")
        }
        if liveSection == .soon {
            return String(localized: "скоро", comment: "Deed holding: soon")
        }
        if liveSection == .postponed {
            return String(localized: "отложили", comment: "Deed holding: postponed")
        }
        return String(localized: "ещё не начинали", comment: "Deed holding: never")
    }

    static func loudDate(_ date: Date) -> String {
        date.formatted(.dateTime.weekday(.wide).day().month(.wide))
    }

    static func chipDate(_ date: Date) -> String {
        date.formatted(.dateTime.day().month(.abbreviated))
    }

    /// Tick face on the lid, on Use and on Inspect. One catalog trip, not a
    /// ternary of two literals that only accidentally resolves to a key.
    static func tickState(done: Bool) -> String {
        done
            ? String(localized: "готово", comment: "Instance completed")
            : String(localized: "на Сегодня", comment: "Deed holding: on today")
    }

    static func instanceStatus(_ status: InstanceStatus) -> String {
        switch status {
        case .completed:
            return String(localized: "готово", comment: "Instance completed")
        case .prepared:
            return String(localized: "готовится", comment: "Instance prepared")
        case .inProgress:
            return String(localized: "в работе", comment: "Instance in progress")
        }
    }
}
