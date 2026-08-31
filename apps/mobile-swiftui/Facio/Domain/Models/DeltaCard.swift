import Foundation

/// The calm half of the morning (Q6): promised by the rhythm minus done.
/// No offer and no chips — a practice merely behind gets a sentence, not a
/// ladder, and `remaining` never goes negative because doing more than
/// promised is not a debt (P7).
struct DeltaCard: Codable, Sendable, Equatable {
    var subjectId: String
    var promised: Int
    var done: Int
    var remaining: Int

    enum CodingKeys: String, CodingKey {
        case subjectId = "subject_id"
        case promised
        case done
        case remaining
    }
}
