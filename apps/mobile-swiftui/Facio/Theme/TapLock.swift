import Foundation

/// A tap that a gesture already answered must not fire a second time.
///
/// Holding a tile (~0.45s) opens the kebab inspector, and the plain `Button`
/// under the long press still fires on lift — without this the short tap that
/// follows a long press would push Use on top of the inspector. `@State` would
/// update too late for the button action to bail, so this is a reference box
/// read in the same turn. Same job for the swipe-up on the chat miniature.
final class TapLock {
    private(set) var consumed = false

    /// The gesture handled this touch; swallow the tap that comes with it.
    func consume() {
        consumed = true
    }

    /// `false` once, right after a gesture consumed the touch.
    func shouldRunTap() -> Bool {
        if consumed {
            consumed = false
            return false
        }
        return true
    }
}
