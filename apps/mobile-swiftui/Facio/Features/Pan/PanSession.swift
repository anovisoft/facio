import SwiftUI

@Observable
@MainActor
final class PanSession {
    var isOpen = false
    var drag: CGFloat = 0
    var keyboardUp = false

    var gutterEnabled: Bool { !isOpen && !keyboardUp }

    func revealed(width: CGFloat) -> CGFloat {
        min(width, max(0, (isOpen ? width : 0) + drag))
    }

    func open() {
        drag = 0
        isOpen = true
    }

    func close() {
        drag = 0
        isOpen = false
    }

    func endDrag(translation: CGFloat, predicted: CGFloat, width: CGFloat) {
        let projected = (isOpen ? width : 0) + predicted
        if projected > width * 0.35 {
            open()
        } else {
            close()
        }
        _ = translation
    }
}
