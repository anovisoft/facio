import SwiftUI

struct RootView: View {
    @State private var path = NavigationPath()

    var body: some View {
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
}
