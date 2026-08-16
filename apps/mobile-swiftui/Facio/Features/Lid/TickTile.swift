import SwiftUI

struct TickTile: View {
    let widget: Widget
    let onOpen: () -> Void
    let onToggle: () -> Void

    private var done: Bool { widget.payload.done == true || widget.status == .done }

    var body: some View {
        Button(action: onOpen) {
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
                        Image(systemName: done ? "checkmark" : "")
                            .font(.system(size: 15, weight: .bold))
                            .foregroundStyle(.primary)
                            .frame(width: 36, height: 36)
                            .facioCircleGlass(interactive: true)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("галочка")
                    Text(done ? "готово" : "на Сегодня")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .facioGlass(dimmed: done)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
    }
}
