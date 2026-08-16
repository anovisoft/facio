import XCTest
@testable import Facio

final class PackLawTests: XCTestCase {
    func testGapWhenNextTileDoesNotFit() {
        let items = ["a", "b"]
        let packed = PackLaw.packRowMajor(items) { item in
            item == "a" ? CellSize(width: 3, height: 1) : CellSize(width: 2, height: 1)
        }
        XCTAssertEqual(packed.placements[0].column, 0)
        XCTAssertEqual(packed.placements[0].row, 0)
        XCTAssertEqual(packed.placements[1].column, 0)
        XCTAssertEqual(packed.placements[1].row, 1)
        XCTAssertEqual(packed.rowCount, 2)
    }

    func testDoesNotReorderToFillHole() {
        let packed = PackLaw.packRowMajor(["wide", "compact"]) { item in
            item == "wide" ? CellSize(width: 3, height: 2) : CellSize(width: 2, height: 2)
        }
        XCTAssertEqual(packed.placements.map(\.item), ["wide", "compact"])
    }
}
