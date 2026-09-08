import Foundation

/// Where a turn sits in the conversation. The client knows this and the service
/// does not, so it is handed to the desk rather than decoded off the wire.
struct TalkTurnRef: Sendable, Equatable {
    var threadId: String
    var turnId: String
}

/// The one step back. P6 says a visible mutation is **reversible**, and 06
/// AI #2 says the desk is never rewritten without an undo — this is the whole
/// of it: the desk as it stood **before** the last talk turn that changed it,
/// and the address of that turn in the thread.
///
/// One record, never a list. A newer desk-changing turn replaces it, so the
/// offer always belongs to the change the person can still see at the bottom of
/// the conversation. Undoing an undo would be a time machine, which is not this.
struct UndoableTurn: Codable, Sendable, Equatable {
    /// The desk to go back to. Structure only in practice: whatever fingers did
    /// after the turn is merged back over it by `ProgressMergeLaw`.
    var before: DeskSnapshot
    var threadId: String
    /// The turn, not the message: one turn is the person's line, the answer,
    /// and the snapshots under it, and all of them get marked undone together.
    var turnId: String
    var at: Date

    enum CodingKeys: String, CodingKey {
        case before
        case threadId = "thread_id"
        case turnId = "turn_id"
        case at
    }
}
