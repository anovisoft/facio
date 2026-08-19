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

    func testPanWidthCapsAtMax() {
        let width = PanSlideLaw.panWidth(containerWidth: 400, maxWidth: 300, ratio: 0.78)
        XCTAssertEqual(width, 300)
    }

    func testPanWidthUsesRatioWhenNarrow() {
        let width = PanSlideLaw.panWidth(containerWidth: 300, maxWidth: 300, ratio: 0.78)
        XCTAssertEqual(width, 234)
    }

    func testProgressClamps() {
        XCTAssertEqual(PanSlideLaw.progress(revealed: 0, panWidth: 300), 0)
        XCTAssertEqual(PanSlideLaw.progress(revealed: 300, panWidth: 300), 1)
        XCTAssertEqual(PanSlideLaw.progress(revealed: 400, panWidth: 300), 1)
    }

    func testShouldOpenUsesPredictedTravel() {
        XCTAssertFalse(PanSlideLaw.shouldOpen(isOpen: false, predicted: 90, panWidth: 300))
        XCTAssertTrue(PanSlideLaw.shouldOpen(isOpen: false, predicted: 120, panWidth: 300))
        XCTAssertTrue(PanSlideLaw.shouldOpen(isOpen: true, predicted: -50, panWidth: 300))
        XCTAssertFalse(PanSlideLaw.shouldOpen(isOpen: true, predicted: -200, panWidth: 300))
    }

    func testCardRadiusFollowsProgress() {
        XCTAssertEqual(PanSlideLaw.cardRadius(progress: 0, deviceRadius: 54), 0)
        XCTAssertEqual(PanSlideLaw.cardRadius(progress: 1, deviceRadius: 54), 54)
    }

    func testRevealedClampsToPanWidth() {
        XCTAssertEqual(PanSlideLaw.revealed(isOpen: false, drag: 0, panWidth: 300), 0)
        XCTAssertEqual(PanSlideLaw.revealed(isOpen: false, drag: 80, panWidth: 300), 80)
        XCTAssertEqual(PanSlideLaw.revealed(isOpen: true, drag: 0, panWidth: 300), 300)
        XCTAssertEqual(PanSlideLaw.revealed(isOpen: true, drag: -40, panWidth: 300), 260)
        XCTAssertEqual(PanSlideLaw.revealed(isOpen: true, drag: 50, panWidth: 300), 300)
        XCTAssertEqual(PanSlideLaw.revealed(isOpen: false, drag: -20, panWidth: 300), 0)
    }
}
