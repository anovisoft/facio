import SwiftUI

/// The face of one session, drawn inside a carousel slot.
///
/// The same shapes the lid tiles wear — the counter's two fonts, the tick's
/// mark, the reminder's hour — at slot size and with every control taken out.
/// There is no `-` / `+`, no mark to press and no `TimelineView`: a slot is a
/// picture of a day (never-do #6).
struct InstanceFaceView: View {
    let face: InstanceFace
    let selected: Bool
    /// A finished session reads dim, the way a done tile does on the lid.
    let dimmed: Bool

    private var numberSize: CGFloat { selected ? 26 : 20 }
    private var unitSize: CGFloat { selected ? 13 : 11 }
    private var markSize: CGFloat { selected ? 30 : 24 }
    private var tint: Color { dimmed ? .secondary : .primary }

    var body: some View {
        switch face {
        case .counter(let count, let goal):
            counter(count: count, goal: goal)
        case .tick(let done):
            Image(systemName: done ? "checkmark.circle.fill" : "circle")
                .font(.system(size: markSize))
                .foregroundStyle(done ? tint : Color.secondary)
        case .checklist(let done, let total):
            counter(count: done, goal: total)
        case .stepper(let step, let total):
            counter(count: step, goal: total)
        case .reminder(let hour):
            Text(hour.shortLabel)
                .font(.system(size: numberSize, weight: .bold, design: .rounded))
                .foregroundStyle(tint)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        case .timer(let face):
            Text(face)
                .font(.system(size: numberSize, weight: .bold, design: .rounded))
                .monospacedDigit()
                .foregroundStyle(tint)
                .lineLimit(1)
                .minimumScaleFactor(0.7)
        case .blank:
            Color.clear.frame(height: 0)
        }
    }

    /// What VoiceOver reads off the face, on top of the slot's date and status.
    /// The tick says nothing extra — its mark and the status are the same fact.
    static func spoken(_ face: InstanceFace) -> String? {
        switch face {
        case .counter(let count, let goal):
            DisplayCopy.counterFace(count: count, goal: goal)
        case .checklist(let done, let total):
            DisplayCopy.counterFace(count: done, goal: total)
        case .stepper(let step, let total):
            DisplayCopy.counterFace(count: step, goal: total)
        case .reminder(let hour):
            hour.shortLabel
        case .timer(let face):
            face
        case .tick, .blank:
            nil
        }
    }

    /// Two fonts on one line, exactly like the counter tile. Without a goal it
    /// stops after the number — « / 0» is a target nobody named.
    private func counter(count: Int, goal: Int?) -> some View {
        let number = Text("\(count)")
            .font(.system(size: numberSize, weight: .bold, design: .rounded))
            .foregroundStyle(tint)
        let line: Text
        if let goal {
            line = number
                + Text(" / \(goal)")
                .font(.system(size: unitSize, weight: .semibold, design: .rounded))
                .foregroundStyle(.secondary)
        } else {
            line = number
        }
        return line
            .lineLimit(1)
            .minimumScaleFactor(0.7)
    }
}
