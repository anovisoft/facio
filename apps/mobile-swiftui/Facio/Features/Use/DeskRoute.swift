import Foundation

enum DeskRoute: Hashable {
    case use(widgetId: String)
    case inspect(subjectId: String, instanceId: String)
}

struct SubjectRef: Hashable, Identifiable {
    var id: String
}
