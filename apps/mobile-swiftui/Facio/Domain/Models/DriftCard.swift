import Foundation

struct DriftCard: Codable, Sendable, Equatable {
    var subjectId: String
    var silentDays: Int
    var offer: DriftOffer

    enum CodingKeys: String, CodingKey {
        case subjectId = "subject_id"
        case silentDays = "silent_days"
        case offer
    }
}
