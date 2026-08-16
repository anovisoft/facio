import SwiftUI

struct RootView: View {
    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @State private var path = NavigationPath()

    var body: some View {
        @Bindable var talk = talk
        ZStack {
            AtmosphereBackground()
            NavigationStack(path: $path) {
                LidScreen(path: $path)
                    .navigationDestination(for: UseRoute.self) { route in
                        switch route {
                        case .widget(let id):
                            UseScreen(widgetId: id)
                        }
                    }
            }
            .safeAreaInset(edge: .bottom) {
                if !talk.sheetOpen {
                    ComposerDock()
                }
            }
        }
        .sheet(isPresented: $talk.sheetOpen) {
            TalkSheet { widgetId in
                talk.sheetOpen = false
                path.append(UseRoute.widget(widgetId))
            }
        }
        .onReceive(NotificationCenter.default.publisher(for: .facioOpenLid)) { _ in
            path = NavigationPath()
        }
        .task {
            ReminderScheduler.enqueue(snapshot: store.snapshot, now: Date())
        }
    }
}
