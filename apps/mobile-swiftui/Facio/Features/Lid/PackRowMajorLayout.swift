import SwiftUI

struct PackRowMajorLayout: Layout {
    var columns: Int = TileCells.columns
    var gap: CGFloat

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) -> CGSize {
        let width = proposal.width ?? 0
        let cell = cellSide(width: width)
        let packed = pack(subviews)
        let rows = packed.rowCount
        let height = CGFloat(rows) * cell + CGFloat(max(rows - 1, 0)) * gap
        return CGSize(width: width, height: max(height, 0))
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout Void) {
        let cell = cellSide(width: bounds.width)
        for (index, tile) in pack(subviews).placements.enumerated() {
            let x = bounds.minX + CGFloat(tile.column) * (cell + gap)
            let y = bounds.minY + CGFloat(tile.row) * (cell + gap)
            let width = CGFloat(tile.width) * cell + CGFloat(max(tile.width - 1, 0)) * gap
            let height = CGFloat(tile.height) * cell + CGFloat(max(tile.height - 1, 0)) * gap
            subviews[index].place(
                at: CGPoint(x: x, y: y),
                proposal: ProposedViewSize(width: width, height: height)
            )
        }
    }

    private func cellSide(width: CGFloat) -> CGFloat {
        let gaps = CGFloat(columns - 1) * gap
        return max((width - gaps) / CGFloat(columns), 0)
    }

    private func pack(_ subviews: Subviews) -> (placements: [PackedTile<Int>], rowCount: Int) {
        PackLaw.packRowMajor(Array(subviews.indices), sizeOf: { index in
            subviews[index][TileCellSizeKey.self]
        }, columns: columns)
    }
}
