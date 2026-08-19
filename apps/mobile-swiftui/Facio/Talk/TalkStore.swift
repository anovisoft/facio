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

    func lastBinding(subjectId: String) -> (thread: ChatThread, snapshot: ChatSnapshot)? {
        let threads = [current] + archived
        for thread in threads {
            if let snapshot = thread.messages.reversed().compactMap(\.snapshot).first(where: { $0.subjectId == subjectId }) {
                return (thread, snapshot)
            }
        }
        return nil
    }

    func open(threadId: String) {
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
