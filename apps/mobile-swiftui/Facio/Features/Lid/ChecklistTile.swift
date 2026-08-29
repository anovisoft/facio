import SwiftUI

/// A checklist on Today / Lifetime may be ticked in place (04). The whole
/// square still opens Use — the marks are **overlay siblings** of
/// `FacioTileButton`, not buttons nested inside it: a nested button either
/// swallows the tap or fires it twice. Both halves are laid out by the same
/// `rows(...)` builder on a fixed row height, so the marks land exactly on the
/// lines they belong to; in the text half the mark is a clear box, in the
/// overlay the text is hidden (laid out, invisible, and not hit-testable).
struct ChecklistTile: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: (() -> Void)?
    let onToggleItem: ((String) -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    /// Two lines fit a 4×2 tile under a title and a cue. The rest of the list
    /// is one tap away on Use — the tile is a glance, not the whole runtime.
    private static let visibleRows = 2
    private static let rowHeight: CGFloat = 30
    private static let rowSpacing: CGFloat = 4
    private static let markSize: CGFloat = 28

    private var items: [ChecklistItem] { ChecklistLaw.items(of: widget.payload) }
    private var shown: [ChecklistItem] { Array(items.prefix(Self.visibleRows)) }
    private var progress: (done: Int, total: Int) { ChecklistLaw.progress(of: widget.payload) }
    private var done: Bool { widget.status == .done || ChecklistLaw.isDone(widget.payload) }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 8) {
                header
                if let cue, !done {
                    Text(cue.text)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
                Spacer(minLength: 0)
                rows(marksVisible: false)
            }
        }
        .overlay(alignment: .bottomLeading) {
            rows(marksVisible: true)
                .padding(.leading, 16)
                .padding(.bottom, 16)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(
            DisplayCopy.checklistAccessibility(
                title: DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title),
                done: progress.done,
                total: progress.total
            )
        )
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                .font(.headline)
                .foregroundStyle(done ? .secondary : .primary)
                .lineLimit(1)
            Spacer(minLength: 0)
            Text(DisplayCopy.counterFace(count: progress.done, goal: progress.total))
                .font(.subheadline.weight(.semibold).width(.condensed))
                .foregroundStyle(.secondary)
                .padding(.trailing, 28)
            KebabStub()
        }
    }

    /// One layout, drawn twice. `marksVisible` picks which half is real.
    private func rows(marksVisible: Bool) -> some View {
        VStack(alignment: .leading, spacing: Self.rowSpacing) {
            ForEach(shown) { item in
                HStack(spacing: 8) {
                    if marksVisible {
                        mark(for: item)
                    } else {
                        Color.clear.frame(width: Self.markSize, height: Self.markSize)
                    }
                    Text(item.text)
                        .font(.subheadline)
                        .foregroundStyle(item.done ? .secondary : .primary)
                        .strikethrough(item.done, color: .secondary)
                        .lineLimit(1)
                        .opacity(marksVisible ? 0 : 1)
                        .allowsHitTesting(false)
                    Spacer(minLength: 0)
                        .allowsHitTesting(false)
                }
                .frame(height: Self.rowHeight, alignment: .leading)
            }
        }
    }

    @ViewBuilder
    private func mark(for item: ChecklistItem) -> some View {
        let glyph = Image(systemName: item.done ? "checkmark.circle.fill" : "circle")
            .font(.system(size: 22))
            .foregroundStyle(item.done ? .primary : .secondary)
            .frame(width: Self.markSize, height: Self.markSize)
            .contentShape(Rectangle())
        if let onToggleItem {
            Button { onToggleItem(item.id) } label: { glyph }
                .buttonStyle(.plain)
                .accessibilityLabel(DisplayCopy.checklistItemAccessibility(item.text))
        } else {
            // Soon / Postponed: a glance, never a live tick (03, 04).
            glyph.accessibilityHidden(true)
        }
    }
}
