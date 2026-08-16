import SwiftUI

struct TileCellSizeKey: LayoutValueKey {
    static let defaultValue = CellSize(width: 2, height: 2)
}

extension View {
    func tileCellSize(_ size: CellSize) -> some View {
        layoutValue(key: TileCellSizeKey.self, value: size)
    }
}
