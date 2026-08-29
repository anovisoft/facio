import Foundation

/// Where the kebab miniature stands inside a chat.
///
/// 04-domain-model: the chapter is **derived, not stored** — the snapshots of
/// one `instance_id` inside one chat, and "scroll to the chapter" means scroll
/// to the *latest* of them. There is no Chapter entity and the word never
/// reaches the interface; this is a scroll target and nothing else.
struct TalkAnchor: Equatable, Hashable {
    var threadId: String
    /// `nil` — the thread has no snapshot of that instance, so the miniature
    /// shows the tail of the conversation instead of jumping somewhere.
    var messageId: String?
}

enum TalkAnchorLaw {
    /// The chat that **last bound** this subject — by the time of its newest
    /// snapshot, not by when someone last typed in the thread. No such chat
    /// (the subject came from the lid, not from the mouth) → the current one.
    /// The kebab never opens a second messenger and never replaces New chat.
    static func thread(in threads: [ChatThread], current: ChatThread, subjectId: String) -> ChatThread {
        boundThread(in: threads, subjectId: subjectId) ?? current
    }

    static func boundThread(in threads: [ChatThread], subjectId: String) -> ChatThread? {
        threads
            .compactMap { thread -> (thread: ChatThread, at: Date)? in
                let stamps = thread.messages
                    .filter { $0.snapshot?.subjectId == subjectId }
                    .map(\.at)
                guard let latest = stamps.max() else { return nil }
                return (thread, latest)
            }
            .max { $0.at < $1.at }?
            .thread
    }

    /// The latest snapshot of this instance inside this chat. Messages are
    /// appended in order, so the last match is the newest one.
    static func messageId(in thread: ChatThread, instanceId: String) -> String? {
        thread.messages.last { $0.snapshot?.instanceId == instanceId }?.id
    }

    /// Moving the carousel re-resolves the anchor **inside the same chat**; it
    /// never opens another one. An instance with no snapshot here has no
    /// chapter, so the miniature stays where it was (07 Q17).
    static func reanchor(previous: TalkAnchor?, thread: ChatThread, instanceId: String) -> TalkAnchor {
        if let messageId = messageId(in: thread, instanceId: instanceId) {
            return TalkAnchor(threadId: thread.id, messageId: messageId)
        }
        if let previous, previous.threadId == thread.id {
            return previous
        }
        return TalkAnchor(threadId: thread.id, messageId: nil)
    }

    /// The picture the miniature draws: the last few messages up to and
    /// including the anchor. A picture of the conversation, not a runtime and
    /// not a second messenger (never-do #6).
    static func preview(in thread: ChatThread, anchor: TalkAnchor?, limit: Int = 4) -> [ChatMessage] {
        let end: Int
        if let messageId = anchor?.messageId,
           let index = thread.messages.firstIndex(where: { $0.id == messageId })
        {
            end = index + 1
        } else {
            end = thread.messages.count
        }
        let start = max(0, end - limit)
        guard start < end else { return [] }
        return Array(thread.messages[start..<end])
    }
}
