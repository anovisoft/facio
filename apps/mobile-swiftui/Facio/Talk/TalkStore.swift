import Foundation
import Observation

@Observable
@MainActor
final class TalkStore {
    private(set) var current: ChatThread
    private(set) var archived: [ChatThread]
    var draft: String = ""
    var sheetOpen: Bool = false
    var sending: Bool = false
    var errorMessage: String?
    var focusedWidgetId: String?
    /// Where the sheet should stand when it opens: the message the kebab
    /// miniature was showing. Derived scroll target, never a stored chapter.
    private(set) var anchorMessageId: String?
    /// Where the turn that just came back landed in the thread. The desk needs
    /// it to hang its one step back on the snapshot the person is looking at.
    private(set) var lastTurn: TalkTurnRef?

    private let repository: TalkRepository
    private let client: TalkClient
    private let now: () -> Date

    static func live() -> TalkStore {
        do {
            return try TalkStore(
                repository: try TalkRepository.applicationSupport(),
                client: .live()
            )
        } catch {
            fatalError("talk warehouse failed: \(error)")
        }
    }

    init(
        repository: TalkRepository,
        client: TalkClient,
        now: @escaping () -> Date = Date.init
    ) throws {
        self.repository = repository
        self.client = client
        self.now = now
        let loaded = try repository.load(now: now())
        current = loaded.current
        archived = loaded.archived
    }

    var placeholder: String {
        String(localized: "Что сюда на стол?", comment: "Composer placeholder")
    }

    /// A day-0 chip puts its own words in the field and opens the sheet. It
    /// must not send: 03-product leaves the first send to the person, and a
    /// chip that talked for him would be a wizard, not a way in.
    func startDraft(_ text: String) {
        draft = text
        errorMessage = nil
        sheetOpen = true
    }

    func appendUser(_ text: String) {
        let stamp = now()
        current.messages.append(.user(text, at: stamp))
        current.updatedAt = stamp
    }

    var listedThreads: [ChatThread] {
        var rows: [ChatThread] = []
        if !current.messages.isEmpty {
            rows.append(current)
        }
        rows.append(contentsOf: archived)
        return rows
    }

    var threads: [ChatThread] {
        [current] + archived
    }

    /// The chat the kebab jumps to, and where inside it. The chapter is
    /// derived here and nowhere else (04-domain-model).
    func anchor(subjectId: String, instanceId: String, previous: TalkAnchor? = nil) -> TalkAnchor {
        let thread = TalkAnchorLaw.thread(in: threads, current: current, subjectId: subjectId)
        return TalkAnchorLaw.reanchor(previous: previous, thread: thread, instanceId: instanceId)
    }

    func thread(id: String) -> ChatThread? {
        threads.first { $0.id == id }
    }

    /// Bring a thread forward and stand on a message inside it, **without
    /// opening anything**. The kebab expands the talk where it stands, so it
    /// needs the promotion without a second sheet arriving over the inspector.
    @discardableResult
    func promote(threadId: String, anchorMessageId: String? = nil) -> Bool {
        self.anchorMessageId = anchorMessageId
        if current.id == threadId {
            persist()
            return true
        }
        guard let index = archived.firstIndex(where: { $0.id == threadId }) else { return false }
        let chosen = archived.remove(at: index)
        if !current.messages.isEmpty {
            archived.insert(current, at: 0)
            if archived.count > 50 {
                archived = Array(archived.prefix(50))
            }
        }
        current = chosen
        draft = ""
        errorMessage = nil
        persist()
        return true
    }

    func open(threadId: String, anchorMessageId: String? = nil) {
        guard promote(threadId: threadId, anchorMessageId: anchorMessageId) else { return }
        sheetOpen = true
    }

    func newChat() {
        let stamp = now()
        anchorMessageId = nil
        if current.messages.isEmpty {
            current.updatedAt = stamp
            persist()
            return
        }
        archived.insert(current, at: 0)
        if archived.count > 50 {
            archived = Array(archived.prefix(50))
        }
        current = .empty(now: stamp)
        draft = ""
        errorMessage = nil
        persist()
    }

    func send(desk: DeskSnapshot) async -> TalkTurnResponse? {
        await send(utterance: draft, desk: desk)
    }

    /// A line the person picked rather than typed — the «what does this mean?»
    /// item on a selection, or the answer to the one clarity check. It lands in
    /// the current thread as an ordinary reply, not as a second kind of message.
    func send(utterance: String, desk: DeskSnapshot, selection: TalkSelection? = nil) async -> TalkTurnResponse? {
        let text = utterance.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !sending else { return nil }
        draft = ""
        errorMessage = nil
        anchorMessageId = nil
        let stamp = now()
        let history = wireThread
        // One turn, one id: the line, the answer and the snapshots under it.
        let turnId = UUID().uuidString
        lastTurn = nil
        current.messages.append(.user(text, at: stamp, turnId: turnId))
        current.updatedAt = stamp
        sending = true
        persist()
        defer { sending = false }
        let request = TalkTurnRequest(
            utterance: text,
            desk: desk,
            thread: history,
            focusedWidgetId: focusedWidgetId,
            selection: selection,
            threadId: current.id,
            now: stamp
        )
        do {
            let response = try await client.turn(request)
            let done = now()
            current.messages.append(.assistant(response.text, at: done, turnId: turnId))
            for card in response.snapshots {
                current.messages.append(.snapshot(card, at: done, turnId: turnId))
            }
            current.updatedAt = done
            lastTurn = TalkTurnRef(threadId: current.id, turnId: turnId)
            persist()
            return response
        } catch {
            errorMessage = String(localized: "Разговор сейчас без трубы. Крышка работает.", comment: "Talk transport error")
            persist()
            return nil
        }
    }

    /// The person took that turn back. **Nothing is removed** — the line, the
    /// answer and the snapshot stay where they are and start saying they were
    /// undone (04: nothing is deleted as punishment). Archived threads are
    /// marked too, so reopening one from the pan shows the truth.
    func markUndone(threadId: String, turnId: String) {
        let stamp = now()
        mark(&current, threadId: threadId, turnId: turnId, at: stamp)
        for index in archived.indices {
            mark(&archived[index], threadId: threadId, turnId: turnId, at: stamp)
        }
        persist()
    }

    private func mark(_ thread: inout ChatThread, threadId: String, turnId: String, at stamp: Date) {
        guard thread.id == threadId else { return }
        for index in thread.messages.indices where thread.messages[index].turnId == turnId {
            guard thread.messages[index].undoneAt == nil else { continue }
            thread.messages[index].undoneAt = stamp
        }
    }

    /// What the mouth is told about the conversation. An undone turn is left
    /// **out**: the desk travels on the same wire and no longer carries what
    /// that turn wrote, so a history still saying «записал зал» beside a desk
    /// with no gym is an invitation to write it again — a silent rewrite the
    /// person already refused (06 AI #2). The transcript was never the source of
    /// truth (never-do #5); the bubbles stay on screen for the person, not for
    /// the model.
    private var wireThread: [TalkWireMessage] {
        current.messages.filter { !$0.isUndone }.compactMap { message in
            switch message.kind {
            case .user:
                TalkWireMessage(role: "user", text: message.text)
            case .assistant:
                TalkWireMessage(role: "assistant", text: message.text)
            case .snapshot:
                nil
            }
        }
    }

    private func persist() {
        try? repository.save(TalkArchive(current: current, archived: archived))
    }
}
