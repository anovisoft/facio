import SwiftUI

struct DriftTile: View {
    let card: DriftCard
    let storedTitle: String
    let onAnswer: (DriftOffer) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(DisplayCopy.driftLine(subjectId: card.subjectId, stored: storedTitle, silentDays: card.silentDays))
                .font(.headline)
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
            DriftChipFlow(spacing: DriftChipMetrics.spacing) {
                ForEach(DriftOffer.downward, id: \.self) { offer in
                    chip(offer)
                }
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .facioGlass()
    }

    private func chip(_ offer: DriftOffer) -> some View {
        Button {
            onAnswer(offer)
        } label: {
            Text(DisplayCopy.driftChip(offer))
                .font(.subheadline.weight(.semibold))
                .lineLimit(1)
                .truncationMode(.tail)
                .frame(maxWidth: DriftChipMetrics.labelMaxWidth)
        }
        .accessibilityLabel(DisplayCopy.driftChip(offer))
        .controlSize(.small)
        .buttonBorderShape(.capsule)
        .modifier(DriftChipChrome(prominent: offer == card.offer))
        .frame(height: DriftChipMetrics.height)
        .fixedSize(horizontal: true, vertical: false)
    }
}

private enum DriftChipMetrics {
    static let height: CGFloat = 32
    static let maxWidth: CGFloat = 152
    static let labelMaxWidth: CGFloat = 128
    static let spacing: CGFloat = 8
}

private struct DriftChipChrome: ViewModifier {
    var prominent: Bool

    func body(content: Content) -> some View {
        if prominent {
            content.buttonStyle(.borderedProminent)
        } else {
            content.buttonStyle(.bordered)
        }
    }
}

/// Hug each chip’s text, wrap when the row is full. Do not stretch to fill.
private struct DriftChipFlow: Layout {
    var spacing: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) -> CGSize {
        arrange(in: proposal.width ?? 0, subviews: subviews).size
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) {
        for (subview, frame) in zip(subviews, arrange(in: bounds.width, subviews: subviews).frames) {
            subview.place(
                at: CGPoint(x: bounds.minX + frame.minX, y: bounds.minY + frame.minY),
                proposal: ProposedViewSize(frame.size)
            )
        }
    }

    private func arrange(in width: CGFloat, subviews: Subviews) -> (size: CGSize, frames: [CGRect]) {
        let limit = max(width, 0)
        var frames: [CGRect] = []
        var x: CGFloat = 0
        var y: CGFloat = 0
        var rowHeight: CGFloat = 0
        for subview in subviews {
            let ideal = subview.sizeThatFits(.unspecified)
            let size = CGSize(
                width: min(ideal.width, DriftChipMetrics.maxWidth),
                height: DriftChipMetrics.height
            )
            if limit > 0, x > 0, x + size.width > limit {
                y += rowHeight + spacing
                x = 0
                rowHeight = 0
            }
            frames.append(CGRect(origin: CGPoint(x: x, y: y), size: size))
            x += size.width + spacing
            rowHeight = max(rowHeight, size.height)
        }
        let usedWidth = frames.map(\.maxX).max() ?? 0
        let usedHeight = frames.map(\.maxY).max() ?? 0
        return (CGSize(width: limit > 0 ? limit : usedWidth, height: usedHeight), frames)
    }
}
