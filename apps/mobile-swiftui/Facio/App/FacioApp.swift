import SwiftUI

@main
struct FacioApp: App {
    @State private var store: DeskStore

    init() {
        do {
            let repository = try DeskRepository.applicationSupport()
            _store = State(initialValue: try DeskStore(repository: repository))
        } catch {
            fatalError("desk warehouse failed: \(error)")
        }
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
        }
    }
}
