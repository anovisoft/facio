import SwiftUI
import UIKit

enum FacioPalette {
    static let gridGap: CGFloat = 12
    static let pagePadding: CGFloat = 20
    static let tileRadius: CGFloat = 26
    static let panGutter: CGFloat = 20
    static let panMaxWidth: CGFloat = 300
    static let panWidthRatio: CGFloat = 0.78

    /// Matches the iPhone display corner when available; continuous 54 otherwise.
    @MainActor
    static var deviceCornerRadius: CGFloat {
        let screen: UIScreen = {
            for scene in UIApplication.shared.connectedScenes {
                guard let windowScene = scene as? UIWindowScene else { continue }
                if let window = windowScene.windows.first(where: { $0.isKeyWindow }) {
                    return window.screen
                }
            }
            return UIScreen.main
        }()
        if let radius = screen.value(forKey: "displayCornerRadius") as? CGFloat, radius > 1 {
            return radius
        }
        return 54
    }
}
