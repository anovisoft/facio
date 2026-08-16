import SwiftUI

struct RootView: View {
    @Environment(DeskStore.self) private var store
    @State private var path = NavigationPath()

    var body: some View {
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
        }
        .onReceive(NotificationCenter.default.publisher(for: .facioOpenLid)) { _ in
            path = NavigationPath()
        }
        .task {
            ReminderScheduler.enqueue(snapshot: store.snapshot, now: Date())
        }
    }
}
