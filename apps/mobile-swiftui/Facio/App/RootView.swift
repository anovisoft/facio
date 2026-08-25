import SwiftUI

struct RootView: View {
    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @State private var path = NavigationPath()
    @State private var pan = PanSession()
    @State private var kebab: SubjectRef?
    @State private var pendingTalk: PendingTalk?

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
                }
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
        .sheet(item: $kebab, onDismiss: presentPendingTalk) { target in
            KebabInspector(
                subjectId: target.id,
                startingInstanceId: store.preferredInstanceId(subjectId: target.id) ?? "",
                onInspect: { subjectId, instanceId in
                    kebab = nil
                    path.append(DeskRoute.inspect(subjectId: subjectId, instanceId: instanceId))
                },
                onTalk: { threadId in
                    pendingTalk = threadId.map { .existing($0) } ?? .fresh
                    kebab = nil
                }
            )
            .presentationDetents([.height(440)])
            .presentationDragIndicator(.visible)
        }
        .sheet(isPresented: $talk.sheetOpen) {
            TalkSheet { card in
                talk.sheetOpen = false
                if store.subject(id: card.subjectId)?.status == .paused {
                    path.append(DeskRoute.inspect(subjectId: card.subjectId, instanceId: card.instanceId))
                } else {
                    path.append(DeskRoute.use(widgetId: card.widgetId))
                }
            }
        }
        .onChange(of: path.count) { _, count in
            if count > 0 { pan.close() }
        }
        .onReceive(NotificationCenter.default.publisher(for: .facioOpenLid)) { _ in
            path = NavigationPath()
        }
        .task {
            ReminderScheduler.enqueue(snapshot: store.snapshot, now: Date())
        }
    }

    private func presentPendingTalk() {
        guard let pendingTalk else { return }
        self.pendingTalk = nil
        switch pendingTalk {
        case .existing(let threadId):
            talk.open(threadId: threadId)
        case .fresh:
            talk.sheetOpen = true
        }
    }
}

private enum PendingTalk: Equatable {
    case existing(String)
    case fresh
}
