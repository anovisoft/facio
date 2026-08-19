import UIKit

/// Window reads for pan chrome. Lid width always comes from the layout container,
/// never from here. `width` is only the pan's fraction of the device.
enum WindowMetrics {
    /// Matches the iPhone display corner when available; continuous 54 otherwise.
    @MainActor
    static var displayCornerRadius: CGFloat {
        let screen = keyWindow?.screen ?? UIScreen.main
        if let radius = screen.value(forKey: "displayCornerRadius") as? CGFloat, radius > 1 {
            return radius
        }
        return 54
    }

    @MainActor
    static var width: CGFloat {
        let fromWindow = keyWindow?.bounds.width ?? 0
        if fromWindow > 1 { return fromWindow }
        return UIScreen.main.bounds.width
    }

    /// Host ignores the safe area so the lid card can be full-bleed.
    /// `.safeAreaPadding` is a no-op there — pad the pan with these insets.
    @MainActor
    static var safeArea: UIEdgeInsets {
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
