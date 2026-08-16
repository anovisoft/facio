import Foundation

enum RankBand: String, Codable, Sendable, Equatable {
    case inProgress = "in_progress"
    case overdue
    case unansweredMorning = "unanswered_morning"
    case driftCard = "drift_card"
    case soonByTime = "soon_by_time"
    case todayIncomplete = "today_incomplete"
    case todayDone = "today_done"

    var sortIndex: Int {
        switch self {
        case .inProgress: 0
        case .overdue: 1
        case .unansweredMorning: 2
        case .driftCard: 3
        case .soonByTime: 4
        case .todayIncomplete: 5
        case .todayDone: 6
        }
    }
}
