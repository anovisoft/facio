import SwiftUI

struct RootView: View {
    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @Environment(\.scenePhase) private var scenePhase
    @State private var path = NavigationPath()
    @State private var pan = PanSession()
    @State private var kebab: SubjectRef?
    /// Built here, not in `FacioApp.init` — the warehouse is a `@State`
    /// factory and this hangs off the same instance.
    @State private var sync: DeskSyncCoordinator?
    @State private var settingsOpen = false
    /// Q32's one check, waiting for the lid. Held until the stack is back at
    /// root: the check follows a finished case, and a sheet racing the pop off
    /// Use is not a calm question.
    @State private var clarityCheck: SubjectRef?
    @State private var pendingClarity: String?

    var body: some View {
        @Bindable var talk = talk
        PanHost(pan: pan, enabled: path.isEmpty) {
            PanScreen(
                onOpenTalk: { threadId in
                    pan.close()
                    talk.open(threadId: threadId)
                },
                onOpenDeed: { subjectId in
                    pan.close()
                    kebab = SubjectRef(id: subjectId)
                },
                onOpenSettings: { settingsOpen = true }
            )
        } content: {
            NavigationStack(path: $path) {
                LidScreen(path: $path, onKebab: { kebab = SubjectRef(id: $0) })
                    .navigationDestination(for: DeskRoute.self) { route in
                        switch route {
                        case .use(let id):
                            UseScreen(widgetId: id)
                        case .inspect(let subjectId, let instanceId):
                            InspectScreen(subjectId: subjectId, instanceId: instanceId)
                        }
                    }
            }
        }
        .environment(pan)
        // One sheet, and the talk grows inside it. The old hand-over through
        // `onDismiss` is gone: closing the kebab to open the mouth is exactly
        // the substitution the PO reported.
        .sheet(item: $kebab) { target in
            KebabInspector(
                subjectId: target.id,
                startingInstanceId: store.preferredInstanceId(subjectId: target.id) ?? "",
                onInspect: { subjectId, instanceId in
                    kebab = nil
                    path.append(DeskRoute.inspect(subjectId: subjectId, instanceId: instanceId))
                },
                onOpenSnapshot: { card in
                    kebab = nil
                    openSnapshot(card)
                },
                onClose: { kebab = nil }
            )
        }
        .sheet(isPresented: $talk.sheetOpen) {
            TalkSheet { card in
                talk.sheetOpen = false
                openSnapshot(card)
            }
        }
        .sheet(isPresented: $settingsOpen) {
            if let sync {
                SettingsScreen(sync: sync) { settingsOpen = false }
            }
        }
        .sheet(item: $clarityCheck) { target in
            ClarityCheckSheet { answer in
                clarityCheck = nil
                answerClarity(answer)
            }
            .id(target.id)
        }
        // Spending the check is the store's business, showing it is this
        // view's. Marked the moment it is scheduled, so a dismissed sheet is
        // still a spent check — asked once means once.
        .onChange(of: store.clarificationAsk) { _, subjectId in
            guard let subjectId else { return }
            pendingClarity = subjectId
            store.markClarificationAsked(subjectId: subjectId)
            presentPendingClarity()
        }
        .onChange(of: path.count) { _, count in
            if count > 0 {
                pan.close()
            } else {
                presentPendingClarity()
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .facioOpenLid)) { _ in
            path = NavigationPath()
        }
        // Local changes reach the server without a hook inside `commit`.
        // Silent without a session — the lid stays a local device.
        .onChange(of: store.snapshot) { _, _ in
            sync?.syncSoon()
        }
        .onChange(of: scenePhase) { _, phase in
            // Coming back on a new day is the only thing that makes a case
            // missing (Q34), so the top-up rides the same wake-up as the sync.
            if phase == .active { store.ensureOccurrences() }
            guard let sync, phase == .active || phase == .background else { return }
            Task { await sync.sync() }
        }
        .task {
            store.ensureOccurrences()
            ReminderScheduler.enqueue(snapshot: store.snapshot, now: Date())
            let coordinator = sync ?? DeskSyncCoordinator(deskStore: store)
            sync = coordinator
            await coordinator.sync()
        }
    }

    private func presentPendingClarity() {
        guard path.isEmpty, kebab == nil, !talk.sheetOpen, let subjectId = pendingClarity else { return }
        pendingClarity = nil
        clarityCheck = SubjectRef(id: subjectId)
    }

    /// The answer is an ordinary reply in the current thread — the same wire,
    /// the same bubble. Opening the thread is the point: an answer the person
    /// never sees is the founding bug again.
    private func answerClarity(_ answer: String) {
        talk.sheetOpen = true
        Task {
            let response = await talk.send(utterance: answer, desk: store.snapshot)
            if let response {
                store.applyTalk(response.desk, toolCalls: response.toolCalls, turn: talk.lastTurn)
            }
        }
    }

    /// A centered snapshot is a picture; tapping it goes to the live object.
    /// A paused practice has nothing to do right now, so it opens Inspect.
    private func openSnapshot(_ card: ChatSnapshot) {
        if store.subject(id: card.subjectId)?.status == .paused {
            path.append(DeskRoute.inspect(subjectId: card.subjectId, instanceId: card.instanceId))
        } else {
            path.append(DeskRoute.use(widgetId: card.widgetId))
        }
    }
}
