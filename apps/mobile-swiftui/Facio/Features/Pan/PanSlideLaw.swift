import CoreGraphics

enum PanSlideLaw {
    static let openThreshold: CGFloat = 0.35
    static let fallbackContainer = CGSize(width: 390, height: 844)

    /// Lid is always the container size. Origin.x is how far the pan is revealed.
    static func lidFrame(in container: CGSize, revealed: CGFloat) -> CGRect {
        CGRect(x: revealed, y: 0, width: container.width, height: container.height)
    }

    static func panFrame(in container: CGSize, panWidth: CGFloat) -> CGRect {
        CGRect(x: 0, y: 0, width: panWidth, height: container.height)
    }

    static func panWidth(containerWidth: CGFloat, maxWidth: CGFloat, ratio: CGFloat) -> CGFloat {
        min(maxWidth, max(0, containerWidth) * ratio)
    }

    static func revealed(isOpen: Bool, drag: CGFloat, panWidth: CGFloat) -> CGFloat {
        min(panWidth, max(0, (isOpen ? panWidth : 0) + drag))
    }

    static func progress(revealed: CGFloat, panWidth: CGFloat) -> CGFloat {
        min(1, max(0, revealed / max(panWidth, 1)))
    }

    static func cardRadius(progress: CGFloat, deviceRadius: CGFloat) -> CGFloat {
        deviceRadius * progress
    }

    static func shouldOpen(isOpen: Bool, predicted: CGFloat, panWidth: CGFloat) -> Bool {
        let projected = (isOpen ? panWidth : 0) + predicted
        return projected > panWidth * openThreshold
    }
}
