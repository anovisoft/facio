import SwiftUI

struct ReminderTile: View {
    let widget: Widget
    let cue: Cue?
    let window: TimeWindow?
    let onOpen: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    private var done: Bool { widget.status == .done }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(done ? .secondary : .primary)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    KebabStub()
                }
                Spacer(minLength: 0)
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    if let window {
                        Text(window.latestBy.shortLabel)
                            .font(.system(size: 28, weight: .bold, design: .rounded))
                            .foregroundStyle(done ? .secondary : .primary)
                    }
                    if let cue {
                        Text(cue.text)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(done ? .secondary : .primary)
                            .lineLimit(1)
                    }
                    Spacer(minLength: 0)
                }
            }
        }
        .accessibilityLabel(accessibilityLabel)
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    private var accessibilityLabel: String {
        let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
        if done { return "\(title), готово" }
        let deadline = window.map(DisplayCopy.succeedBy)
        return [title, deadline, cue?.text].compactMap { $0 }.joined(separator: ", ")
    }
}
