import SwiftUI

/// The occurrences of one subject inside one period, drawn **once** (Q34).
///
/// Seven identical squares were the failure: none of them carried an hour, so
/// «отметить именно проверку в 15:00» was a guess, and seven tiles of one
/// practice pushed everything else off Сегодня. This is the same seven checks —
/// the law still counts seven — wearing one tile.
///
/// It borrows the stepper's compactness and refuses its **pointer**. Every mark
/// is its own check: tapping 15:00 closes 15:00, and the 12:00 nobody got to
/// stays open and stays on screen. There is no "current" mark to advance,
/// because a pointer cannot say *which* three of seven happened, and that is
/// the whole product.
///
/// Layout follows the checklist's rule: the whole square opens Use, and the
/// marks are **overlay siblings** of `FacioTileButton`, never buttons nested
/// inside it — a nested button swallows the tap or fires it twice.
struct GroupTile: View {
    let face: GroupFace
    let cue: Cue?
    let onOpen: (() -> Void)?
    let onClose: ((String) -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    private static let markSize: CGFloat = 28
    private static let rowHeight: CGFloat = 46

    private var done: Bool { face.done == face.total }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 8) {
                header
                Spacer(minLength: 0)
                hourLine
                marks(visible: false)
            }
        }
        .overlay(alignment: .bottomLeading) {
            marks(visible: true)
                .padding(.leading, 16)
                .padding(.bottom, 16)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel(
            DisplayCopy.groupAccessibility(
                title: DisplayCopy.title(subjectId: face.subjectId, stored: face.title),
                done: face.done,
                total: face.total
            )
        )
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    private var header: some View {
        HStack(alignment: .top, spacing: 8) {
            Text(DisplayCopy.title(subjectId: face.subjectId, stored: face.title))
                .font(.headline)
                .foregroundStyle(done ? .secondary : .primary)
                .lineLimit(1)
            Spacer(minLength: 0)
            Text(DisplayCopy.counterFace(count: face.done, goal: face.total))
                .font(.subheadline.weight(.semibold).width(.condensed))
                .foregroundStyle(.secondary)
                .padding(.trailing, 28)
            KebabStub()
        }
    }

    /// The nearest hour still ahead, large — the one thing the seven squares
    /// never had. When the day is finished there is no hour left to name, so
    /// the line says so instead of inventing one.
    private var hourLine: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            if let hour = face.nextHour {
                Text(hour.shortLabel)
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundStyle(done ? .secondary : .primary)
            } else {
                Text(DisplayCopy.tickState(done: true))
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            if let cue, !done {
                Text(cue.text)
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.primary)
                    .lineLimit(1)
            }
            Spacer(minLength: 0)
        }
    }

    /// One row, drawn twice. `visible` picks which half is real: the copy inside
    /// the button reserves the space, the copy in the overlay carries the taps.
    private func marks(visible: Bool) -> some View {
        HStack(spacing: 0) {
            ForEach(face.marks) { mark in
                VStack(spacing: 2) {
                    if visible {
                        glyph(for: mark)
                    } else {
                        Color.clear.frame(width: Self.markSize, height: Self.markSize)
                    }
                    Text(mark.hour?.shortLabel ?? "")
                        .font(.caption2.monospacedDigit())
                        .foregroundStyle(.secondary)
                        .lineLimit(1)
                        .minimumScaleFactor(0.7)
                        .opacity(visible ? 0 : 1)
                        .allowsHitTesting(false)
                }
                .frame(maxWidth: .infinity)
            }
        }
        .frame(height: Self.rowHeight, alignment: .bottom)
        .padding(.trailing, 16)
    }

    @ViewBuilder
    private func glyph(for mark: GroupMark) -> some View {
        let symbol = Image(systemName: mark.done ? "checkmark.circle.fill" : "circle")
            .font(.system(size: 22))
            .foregroundStyle(mark.done ? .primary : .secondary)
            .frame(width: Self.markSize, height: Self.markSize)
            .contentShape(Rectangle())
        if let onClose {
            Button { onClose(mark.widgetId) } label: { symbol }
                .buttonStyle(.plain)
                .accessibilityLabel(DisplayCopy.groupMarkAccessibility(mark.hour))
                .accessibilityAddTraits(mark.done ? [.isSelected] : [])
        } else {
            // Soon / Postponed stay a glance, never a live mark (03, 04).
            symbol.accessibilityHidden(true)
        }
    }
}
