import XCTest
@testable import Facio

final class PanSlideLawTests: XCTestCase {
    private let container = CGSize(width: 402, height: 874)

    func testClosedLidFillsContainer() {
        let lid = PanSlideLaw.lidFrame(in: container, revealed: 0)
        XCTAssertEqual(lid, CGRect(origin: .zero, size: container))
    }

    func testOpenLidKeepsContainerWidth() {
        let lid = PanSlideLaw.lidFrame(in: container, revealed: 300)
        XCTAssertEqual(lid.width, container.width)
        XCTAssertEqual(lid.height, container.height)
        XCTAssertEqual(lid.minX, 300)
    }

    func testPanSitsOnTheLeadingEdge() {
        let pan = PanSlideLaw.panFrame(in: container, panWidth: 300)
        XCTAssertEqual(pan, CGRect(x: 0, y: 0, width: 300, height: container.height))
    }
}
