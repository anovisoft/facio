import SwiftUI

@main
struct FacioApp: App {
    @State private var store = DeskStore.live()
    @State private var talk = TalkStore.live()

    init() {
        FacioNotificationRouter.shared.install()
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .environment(talk)
        }
    }
}
