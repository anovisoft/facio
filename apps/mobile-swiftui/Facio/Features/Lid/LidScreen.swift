import SwiftUI

struct LidScreen: View {
    @Environment(DeskStore.self) private var store
    @Environment(PanSession.self) private var pan
    @Environment(\.panWidth) private var panWidth
    @Binding var path: NavigationPath
    var onKebab: (String) -> Void

    private var restoredLeading: CGFloat {
        pan.revealed(width: panWidth) > 8 ? FacioPalette.pagePadding : 0
    }

    var body: some View {
        ScrollView {
            LidFeed(
                projection: store.lid,
                cueFor: store.surfaceCue(for:),
                windowFor: store.windowFor(subjectId:),
                subjectTitle: { store.subject(id: $0)?.title ?? $0 },
                showsSubject: store.showsOnLid(subjectId:),
                surfacesDrift: store.surfaces,
                onOpen: { path.append(DeskRoute.use(widgetId: $0)) },
                onInspect: { path.append(DeskRoute.inspect(subjectId: $0, instanceId: $1)) },
                onKebab: onKebab,
                onToggleTick: store.toggleTick,
                onSurfaced: { store.markCueSurfaced(widgetId: $0, place: "tile") },
                onAnswerDrift: store.answerDrift
            )
            .padding(.leading, FacioPalette.pagePadding - restoredLeading)
            .padding(.trailing, FacioPalette.pagePadding)
            .padding(.bottom, 32)
        }
        .scrollIndicators(.hidden)
        .background(.clear)
        .overlay(alignment: .leading) {
            PanGutter()
        }
        .safeAreaPadding(.leading, restoredLeading)
        .navigationTitle("Facio")
        .toolbarTitleDisplayMode(.large)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                Button {
                    pan.open()
                } label: {
                    Image(systemName: "line.3.horizontal")
                }
                .accessibilityLabel("Сковородка")
            }
        }
        .facioChrome()
        .facioComposerDock()
    }
}

#Preview {
    @Previewable @State var path = NavigationPath()
    @Previewable @State var pan = PanSession()
    NavigationStack(path: $path) {
        LidScreen(path: $path, onKebab: { _ in })
            .navigationDestination(for: DeskRoute.self) { route in
                switch route {
                case .use(let id):
                    UseScreen(widgetId: id)
                case .inspect(let subjectId, let instanceId):
                    InspectScreen(subjectId: subjectId, instanceId: instanceId)
                }
            }
    }
    .environment(previewStore())
    .environment(previewTalk())
    .environment(pan)
}

@MainActor
private func previewStore() -> DeskStore {
    let directory = FileManager.default.temporaryDirectory.appending(path: "facio-preview", directoryHint: .isDirectory)
    try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let repository = DeskRepository(directory: directory)
    return try! DeskStore(repository: repository)
}

@MainActor
private func previewTalk() -> TalkStore {
    let directory = FileManager.default.temporaryDirectory.appending(path: "facio-preview-talk", directoryHint: .isDirectory)
    try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    return try! TalkStore(repository: TalkRepository(directory: directory), client: .live())
}
