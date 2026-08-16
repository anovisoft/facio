import SwiftUI

struct LidScreen: View {
    @Environment(DeskStore.self) private var store
    @Binding var path: NavigationPath

    var body: some View {
        ScrollView {
            LidFeed(
                projection: store.lid,
                cueFor: store.cueFor(subjectId:),
                onOpen: { path.append(UseRoute.widget($0)) },
                onToggleTick: store.toggleTick,
                onSurfaced: { store.markCueSurfaced(widgetId: $0, place: "tile") }
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
            .environment(previewStore())
            .navigationDestination(for: UseRoute.self) { route in
                if case .widget(let id) = route {
                    UseScreen(widgetId: id)
                }
            }
    }
}

@MainActor
private func previewStore() -> DeskStore {
    let directory = FileManager.default.temporaryDirectory.appending(path: "facio-preview", directoryHint: .isDirectory)
    try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    let repository = DeskRepository(directory: directory)
    return try! DeskStore(repository: repository)
}
