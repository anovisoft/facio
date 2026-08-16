import Foundation

enum TileSize: String, Codable, Sendable, Equatable {
    case compact = "2x2"
    case banner = "4x1"
    case wide = "4x2"
    case full = "4x4"
    case oneByTwo = "1x2"
    case oneByFour = "1x4"
    case twoByFour = "2x4"
    case threeByFour = "3x4"

    static let defaultCompact = TileSize.compact
}
