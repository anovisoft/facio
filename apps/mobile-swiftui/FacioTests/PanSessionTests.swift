import XCTest
@testable import Facio

@MainActor
final class PanSessionTests: XCTestCase {
    func testEndDragOpensPastThreshold() {
        let pan = PanSession()
        pan.endDrag(predicted: 120, width: 300)
        XCTAssertTrue(pan.isOpen)
        XCTAssertEqual(pan.drag, 0)
    }

    func testEndDragClosesWhenPredictedFallsShort() {
        let pan = PanSession()
        pan.open()
        pan.endDrag(predicted: -200, width: 300)
        XCTAssertFalse(pan.isOpen)
    }

    func testKeyboardDisablesGutter() {
        let pan = PanSession()
        XCTAssertTrue(pan.gutterEnabled)
        pan.keyboardUp = true
        XCTAssertFalse(pan.gutterEnabled)
        pan.keyboardUp = false
        pan.open()
        XCTAssertFalse(pan.gutterEnabled)
    }
}
