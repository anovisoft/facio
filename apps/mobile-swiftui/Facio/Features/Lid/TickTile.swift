import SwiftUI

struct TickTile: View {
    let widget: Widget
    let onOpen: () -> Void
    let onToggle: () -> Void

    private var done: Bool { widget.payload.done == true || widget.status == .done }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen) {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .top, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(done ? .secondary : .primary)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    KebabStub()
                }
                Spacer(minLength: 0)
                HStack(spacing: 10) {
                    Button(action: onToggle) {
                        Image(systemName: done ? "checkmark.circle.fill" : "circle")
                            .font(.title2)
                            .foregroundStyle(done ? .primary : .secondary)
                            .frame(width: 36, height: 36)
                            .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("галочка")
                    Text(done ? "готово" : "на Сегодня")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .accessibilityLabel(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
    }
}
