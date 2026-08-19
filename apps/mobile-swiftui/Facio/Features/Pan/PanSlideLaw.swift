import CoreGraphics

enum PanSlideLaw {
    /// Lid is always the container size. Origin.x is how far the pan is revealed.
    static func lidFrame(in container: CGSize, revealed: CGFloat) -> CGRect {
        CGRect(x: revealed, y: 0, width: container.width, height: container.height)
    }

    static func panFrame(in container: CGSize, panWidth: CGFloat) -> CGRect {
        CGRect(x: 0, y: 0, width: panWidth, height: container.height)
    }
}
