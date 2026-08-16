import Foundation
import UserNotifications

extension Notification.Name {
    static let facioOpenLid = Notification.Name("facioOpenLid")
}

@MainActor
final class FacioNotificationRouter: NSObject, UNUserNotificationCenterDelegate {
    static let shared = FacioNotificationRouter()

    func install() {
        UNUserNotificationCenter.current().delegate = self
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.banner, .sound, .list]
    }

    nonisolated func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let info = response.notification.request.content.userInfo
        guard info[ReminderScheduler.openLidKey] as? String == ReminderScheduler.openLidValue else { return }
        await MainActor.run {
            NotificationCenter.default.post(name: .facioOpenLid, object: nil)
        }
    }
}
