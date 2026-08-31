import Foundation

/// One line of a checklist. `done` is finger state on that line and nothing
/// more — no per-item timestamp, no score. How many lines are ticked is
/// counted by `ChecklistLaw`, never stored: a saved number and a list of ticks
/// are two truths about the same thing, and they drift the first time a tick
/// happens offline (Q20).
struct ChecklistItem: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var text: String
    var done: Bool

    init(id: String, text: String, done: Bool = false) {
        self.id = id
        self.text = text
        self.done = done
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        text = try container.decode(String.self, forKey: .text)
        done = try container.decodeIfPresent(Bool.self, forKey: .done) ?? false
    }
}
