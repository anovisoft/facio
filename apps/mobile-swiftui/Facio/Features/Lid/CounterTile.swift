import SwiftUI

struct CounterTile: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: () -> Void
    let onSurfaced: () -> Void

    private var done: Bool { widget.status == .done }
    private var count: Int { widget.payload.count ?? 0 }
    private var target: Int { widget.payload.target ?? 0 }

    var body: some View {
        Button(action: onOpen) {
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
                Text("\(count)")
                    .font(.system(size: 34, weight: .bold, design: .rounded))
                    .foregroundStyle(done ? .secondary : .primary)
                    + Text(" / \(target)")
                    .font(.system(size: 16, weight: .semibold, design: .rounded))
                    .foregroundStyle(.secondary)
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
            .padding(16)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .facioGlass(dimmed: done)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(accessibilityLabel)
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    private var accessibilityLabel: String {
        let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
        if done { return "\(title), готово" }
        if let cue { return "\(title), \(count) из \(target), \(cue.text)" }
        return "\(title), \(count) из \(target)"
    }
}
