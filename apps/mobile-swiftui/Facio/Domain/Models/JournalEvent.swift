import Foundation

enum JournalEventType: String, Codable, Sendable, Equatable {
    case cueWritten = "cue_written"
    case cueSurfaced = "cue_surfaced"
    case cueApplied = "cue_applied"
    case instanceStarted = "instance_started"
    case instanceCompleted = "instance_completed"
    case counterTicked = "counter_ticked"
    case tickToggled = "tick_toggled"
    /// One line of a checklist. Step 1 of the plan reads the same journal for
    /// cue hits and the late sync, so a tick has to be an event, not only a
    /// field that quietly changed under a full-desk write (Q20).
    case checklistItemToggled = "checklist_item_toggled"
    /// A timer run beginning and ending, with the seconds it produced. The
    /// journal is where elapsed time is *recorded*; the payload only ever
    /// remembers when the current run began.
    case timerStarted = "timer_started"
    case timerPaused = "timer_paused"
    /// Where a sequence stands after a beat was pressed. Same reason as the
    /// checklist tick: the late sync has to see the move, not only the field.
    case stepperMoved = "stepper_moved"
    /// A talk turn that changed the desk, taken back by the person in one step
    /// (P6 «reversible», 06 AI #2). An event like any other, so the measurement
    /// slice can read how often the mouth is wrong from the same journal.
    case talkUndone = "talk_undone"
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
