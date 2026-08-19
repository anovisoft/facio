import SwiftUI

@Observable
@MainActor
final class PanSession {
    var isOpen = false
    var drag: CGFloat = 0
    var keyboardUp = false

    var gutterEnabled: Bool { !isOpen && !keyboardUp }

    func open() {
        drag = 0
        isOpen = true
    }

    func close() {
        drag = 0
        isOpen = false
    }

    func endDrag(predicted: CGFloat, width: CGFloat) {
        if PanSlideLaw.shouldOpen(isOpen: isOpen, predicted: predicted, panWidth: width) {
            open()
        } else {
            close()
        }
    }
}
