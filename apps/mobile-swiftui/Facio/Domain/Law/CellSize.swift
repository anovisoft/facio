import Foundation

struct CellSize: Sendable, Equatable {
    var width: Int
    var height: Int
}

enum TileCells {
    static let columns = 4

    static func size(for tile: TileSize?) -> CellSize {
        switch tile ?? .defaultCompact {
        case .compact: CellSize(width: 2, height: 2)
        case .banner: CellSize(width: 4, height: 1)
        case .wide: CellSize(width: 4, height: 2)
        case .full: CellSize(width: 4, height: 4)
        case .oneByTwo: CellSize(width: 1, height: 2)
        case .oneByFour: CellSize(width: 1, height: 4)
        case .twoByFour: CellSize(width: 2, height: 4)
        case .threeByFour: CellSize(width: 3, height: 4)
        }
    }
}

struct PackedTile<Item> {
    var item: Item
    var column: Int
    var row: Int
    var width: Int
    var height: Int
}

enum PackLaw {
    static func packRowMajor<Item>(
        _ items: [Item],
        sizeOf: (Item) -> CellSize,
        columns: Int = TileCells.columns
    ) -> (placements: [PackedTile<Item>], rowCount: Int) {
        var placements: [PackedTile<Item>] = []
        var row = 0
        var column = 0
        var rowHeight = 0

        for item in items {
            let size = sizeOf(item)
            let width = min(max(size.width, 1), columns)
            let height = max(size.height, 1)
            if column + width > columns {
                row += rowHeight > 0 ? rowHeight : 1
                column = 0
                rowHeight = 0
            }
            placements.append(PackedTile(item: item, column: column, row: row, width: width, height: height))
            column += width
            rowHeight = max(rowHeight, height)
        }

        let rowCount = placements.map { $0.row + $0.height }.max() ?? 0
        return (placements, rowCount)
    }
}
