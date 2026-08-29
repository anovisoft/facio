import SwiftUI

struct TickTile: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: (() -> Void)?
    let onToggle: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

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
                if !done, let cue {
                    Text(cue.text)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                HStack(spacing: 10) {
                    Color.clear
                        .frame(width: 36, height: 36)
                    Text(DisplayCopy.tickState(done: done))
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                }
            }
        }
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
        .overlay(alignment: .bottomLeading) {
            mark
                .padding(.leading, 16)
                .padding(.bottom, 16)
        }
        .accessibilityLabel(accessibilityLabel)
    }

    private var accessibilityLabel: String {
        let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
        guard !done, let cue else { return title }
        return String(localized: "\(title), \(cue.text)", comment: "Tick tile accessibility: title and its do-time cue")
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
