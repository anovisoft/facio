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
        let screen = keyWindow?.screen ?? UIScreen.main
        if let radius = screen.value(forKey: "displayCornerRadius") as? CGFloat, radius > 1 {
            return radius
        }
        return 54
    }

    @MainActor
    static var deviceWidth: CGFloat {
        let fromWindow = keyWindow?.bounds.width ?? 0
        if fromWindow > 1 { return fromWindow }
        return UIScreen.main.bounds.width
    }

    /// Window insets. `.safeAreaPadding(.top)` is a no-op under `ignoresSafeArea()`.
    @MainActor
    static var deviceSafeArea: UIEdgeInsets {
        if let insets = keyWindow?.safeAreaInsets, insets.top > 1 {
            return insets
        }
        return UIEdgeInsets(top: 62, left: 0, bottom: 34, right: 0)
    }

    @MainActor
    private static var keyWindow: UIWindow? {
        for scene in UIApplication.shared.connectedScenes {
            guard let windowScene = scene as? UIWindowScene else { continue }
            if let window = windowScene.windows.first(where: { $0.isKeyWindow }) {
                return window
            }
        }
        for scene in UIApplication.shared.connectedScenes {
            guard let windowScene = scene as? UIWindowScene else { continue }
            if let window = windowScene.windows.first {
                return window
            }
        }
        return nil
    }
}
