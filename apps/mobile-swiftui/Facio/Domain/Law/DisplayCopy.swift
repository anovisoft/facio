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
}
