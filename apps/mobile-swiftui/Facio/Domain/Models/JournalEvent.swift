import Foundation

enum JournalEventType: String, Codable, Sendable, Equatable {
    case cueWritten = "cue_written"
    case cueSurfaced = "cue_surfaced"
    case cueApplied = "cue_applied"
    case instanceStarted = "instance_started"
    case instanceCompleted = "instance_completed"
    case counterTicked = "counter_ticked"
    case tickToggled = "tick_toggled"
    case subjectShrunk = "subject_shrunk"
    case subjectRetired = "subject_retired"
    case driftAnswered = "drift_answered"
    /// Q32's one check, per subject. Kept in the journal for the same reason
    /// day zero is a latch on disk and not a `DeskSnapshot` field: the desk is
    /// the wire shape the service also writes, and "he has already been asked"
    /// is this device's business.
    case clarificationAsked = "clarification_asked"
}

struct JournalEvent: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var type: JournalEventType
    var at: Date
    var subjectId: String?
    var widgetId: String?
    var instanceId: String?
    var cueId: String?
    var payload: [String: String]?

    enum CodingKeys: String, CodingKey {
        case id
        case type
        case at
        case subjectId = "subject_id"
        case widgetId = "widget_id"
        case instanceId = "instance_id"
        case cueId = "cue_id"
        case payload
    }
}
