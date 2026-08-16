import SwiftUI

@main
struct FacioApp: App {
    @State private var store = DeskStore.live()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
        }
    }
}
