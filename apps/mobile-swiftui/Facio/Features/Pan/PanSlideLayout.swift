import SwiftUI

struct PanSlideLayout: Layout, Animatable {
    var panWidth: CGFloat
    var revealed: CGFloat

    var animatableData: CGFloat {
        get { revealed }
        set { revealed = newValue }
    }

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        proposal.replacingUnspecifiedDimensions(by: PanSlideLaw.fallbackContainer)
    }

    func placeSubviews(
        in bounds: CGRect,
        proposal: ProposedViewSize,
        subviews: Subviews,
        cache: inout ()
    ) {
        let size = bounds.size
        if let pan = subviews.first {
            let frame = PanSlideLaw.panFrame(in: size, panWidth: panWidth)
            pan.place(
                at: frame.origin,
                anchor: .topLeading,
                proposal: ProposedViewSize(width: frame.width, height: frame.height)
            )
        }
        if subviews.count > 1 {
            let lid = subviews[1]
            let frame = PanSlideLaw.lidFrame(in: size, revealed: revealed)
            lid.place(
                at: frame.origin,
                anchor: .topLeading,
                proposal: ProposedViewSize(width: frame.width, height: frame.height)
            )
        }
    }
}
