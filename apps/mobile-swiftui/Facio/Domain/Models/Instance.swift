import Foundation

struct Instance: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var subjectId: String
    var when: Date
    var status: InstanceStatus

    enum CodingKeys: String, CodingKey {
        case id
        case subjectId = "subject_id"
        case when
        case status
    }
}
