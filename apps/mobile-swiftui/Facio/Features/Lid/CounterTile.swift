import SwiftUI

struct CounterTile: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    private var done: Bool { widget.status == .done }
    private var count: Int { widget.counterCount }
    private var goal: Int? { widget.counterGoal }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(done ? .secondary : .primary)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    KebabStub()
                }
                Spacer(minLength: 0)
                face
                if done {
                    Text("готово")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                } else if let cue {
                    Text(cue.text)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .accessibilityLabel(accessibilityLabel)
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    /// Two fonts, one line. Without a goal the tile stops after the number —
    /// « / 0» would be a target the person never named.
    private var face: Text {
        let number = Text("\(count)")
            .font(.system(size: 34, weight: .bold, design: .rounded))
            .foregroundStyle(done ? .secondary : .primary)
        guard let goal else { return number }
        return number
            + Text(" / \(goal)")
            .font(.system(size: 16, weight: .semibold, design: .rounded))
            .foregroundStyle(.secondary)
    }

    private var accessibilityLabel: String {
        let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
        if done {
            return String(localized: "\(title), готово", comment: "Tile accessibility: done")
        }
        return DisplayCopy.counterAccessibility(title: title, count: count, goal: goal, cue: cue?.text)
    }
}
