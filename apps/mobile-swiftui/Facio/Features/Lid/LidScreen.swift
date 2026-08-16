import SwiftUI

struct LidScreen: View {
    @Environment(DeskStore.self) private var store
    @Binding var path: NavigationPath

    var body: some View {
        ScrollView {
            LidFeed(
                projection: store.lid,
                cueFor: store.surfaceCue(for:),
                windowFor: store.windowFor(subjectId:),
                subjectTitle: { store.subject(id: $0)?.title ?? $0 },
                showsSubject: store.showsOnLid(subjectId:),
                surfacesDrift: store.surfaces,
                onOpen: { path.append(UseRoute.widget($0)) },
                onToggleTick: store.toggleTick,
                onSurfaced: { store.markCueSurfaced(widgetId: $0, place: "tile") },
                onAnswerDrift: store.answerDrift
            )
            .padding(.horizontal, FacioPalette.pagePadding)
            .padding(.bottom, 32)
        }
        .scrollIndicators(.hidden)
        .background(.clear)
        .navigationTitle("Facio")
        .toolbarTitleDisplayMode(.large)
        .facioChrome()
    }
}

#Preview {
    @Previewable @State var path = NavigationPath()
    NavigationStack(path: $path) {
        LidScreen(path: $path)
            .navigationDestination(for: UseRoute.self) { route in
                if case .widget(let id) = route {
                    UseScreen(widgetId: id)
                }
            }
    }
    .environment(previewStore())
    .environment(previewTalk())
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
