import Foundation

struct DeskSnapshot: Codable, Sendable, Equatable {
    var subjects: [Subject]
    var cues: [Cue]
    var instances: [Instance]
    var widgets: [Widget]
}
