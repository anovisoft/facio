import SwiftUI

@main
struct FacioApp: App {
    @State private var store = DeskStore.live()

    init() {
        FacioNotificationRouter.shared.install()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
        }
    }
}
