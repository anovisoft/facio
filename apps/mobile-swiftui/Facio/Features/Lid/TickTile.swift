import SwiftUI

struct TickTile: View {
    let widget: Widget
    let onOpen: (() -> Void)?
    let onToggle: (() -> Void)?
    let onKebab: () -> Void

    private var done: Bool { widget.isTickDone }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
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
                    Color.clear
                        .frame(width: 36, height: 36)
                    Text(done ? "готово" : "на Сегодня")
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .overlay(alignment: .bottomLeading) {
            mark
                .padding(.leading, 16)
                .padding(.bottom, 16)
        }
        .accessibilityLabel(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
    }

    @ViewBuilder
    private var mark: some View {
        let glyph = Image(systemName: done ? "checkmark.circle.fill" : "circle")
            .font(.system(size: 36))
            .foregroundStyle(done ? .primary : .secondary)
            .frame(width: 36, height: 36)
            .contentShape(Rectangle())
        if let onToggle {
            Button(action: onToggle) { glyph }
                .buttonStyle(.plain)
                .accessibilityLabel("галочка")
        } else {
            glyph
                .accessibilityHidden(true)
        }
    }
}
