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

    func open(threadId: String, anchorMessageId: String? = nil) {
        self.anchorMessageId = anchorMessageId
        if current.id == threadId {
            sheetOpen = true
            persist()
            return
        }
        guard let index = archived.firstIndex(where: { $0.id == threadId }) else { return }
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
        sheetOpen = true
        persist()
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
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !sending else { return nil }
        draft = ""
        errorMessage = nil
        anchorMessageId = nil
        let stamp = now()
        let history = wireThread
        current.messages.append(.user(text, at: stamp))
        current.updatedAt = stamp
        sending = true
        persist()
        defer { sending = false }
        let request = TalkTurnRequest(
            utterance: text,
            desk: desk,
            thread: history,
            focusedWidgetId: focusedWidgetId,
            threadId: current.id,
            now: stamp
        )
        do {
            let response = try await client.turn(request)
            let done = now()
            current.messages.append(.assistant(response.text, at: done))
            for card in response.snapshots {
                current.messages.append(.snapshot(card, at: done))
            }
            current.updatedAt = done
            persist()
            return response
        } catch {
            errorMessage = String(localized: "Разговор сейчас без трубы. Крышка работает.", comment: "Talk transport error")
            persist()
            return nil
        }
    }

    private var wireThread: [TalkWireMessage] {
        current.messages.compactMap { message in
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
