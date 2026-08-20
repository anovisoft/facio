import Foundation
import UserNotifications

struct ReminderAlarm: Equatable, Sendable {
    var id: String
    var fireAt: Date
    var title: String
    var body: String
}

enum ReminderScheduler {
    static let idPrefix = "reminder:"
    static let openLidKey = "open"
    static let openLidValue = "lid"

    static func alarmId(widgetId: String) -> String {
        idPrefix + widgetId
    }

    static func checkInAlarmId(subjectId: String) -> String {
        idPrefix + "check-in:" + subjectId
    }

    static func alarms(from snapshot: DeskSnapshot, now: Date) -> [ReminderAlarm] {
        let bySubject = Dictionary(uniqueKeysWithValues: snapshot.subjects.map { ($0.id, $0) })
        var alarms: [ReminderAlarm] = snapshot.widgets.compactMap { widget in
            guard widget.type == .reminder, widget.status != .done else { return nil }
            let subject = bySubject[widget.subjectId]
            if subject?.status == .retired || subject?.status == .paused {
                return nil
            }
            let fireAt = widget.reminderFireAt
            guard let fireAt, fireAt > now else { return nil }
            let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
            let window = subject?.window
            let cue = CueLaw.timingCue(in: snapshot.cues, subjectId: widget.subjectId)
            let deadline = window.map(DisplayCopy.succeedBy)
            let body = [deadline, cue?.text].compactMap { $0 }.joined(separator: " · ")
            return ReminderAlarm(
                id: alarmId(widgetId: widget.id),
                fireAt: fireAt,
                title: title,
                body: body.isEmpty ? title : body
            )
        }
        for subject in snapshot.subjects where subject.status == .paused {
            guard let pausedAt = subject.pausedAt else { continue }
            let fireAt = SubjectLaw.pauseCheckInAt(pausedAt)
            guard fireAt > now else { continue }
            alarms.append(
                ReminderAlarm(
                    id: checkInAlarmId(subjectId: subject.id),
                    fireAt: fireAt,
                    title: DisplayCopy.title(subjectId: subject.id, stored: subject.title),
                    body: DisplayCopy.pauseCheckInBody
                )
            )
        }
        return alarms
    }

    static func enqueue(snapshot: DeskSnapshot, now: Date) {
        Task { await gate.enqueue(snapshot: snapshot, now: now) }
    }

    fileprivate static func sync(snapshot: DeskSnapshot, now: Date) async {
        let center = UNUserNotificationCenter.current()
        let granted = await requestAuthorization(center)
        guard granted else { return }
        await apply(alarms: alarms(from: snapshot, now: now), center: center)
    }

    private static func requestAuthorization(_ center: UNUserNotificationCenter) async -> Bool {
        do {
            return try await center.requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    private static func apply(alarms: [ReminderAlarm], center: UNUserNotificationCenter) async {
        let pending = await center.pendingNotificationRequests()
        let stale = pending.map(\.identifier).filter { $0.hasPrefix(idPrefix) }
        center.removePendingNotificationRequests(withIdentifiers: stale)

        for alarm in alarms {
            let content = UNMutableNotificationContent()
            content.title = alarm.title
            content.body = alarm.body
            content.sound = .default
            content.userInfo = [openLidKey: openLidValue]
            let parts = Calendar.current.dateComponents(
                [.year, .month, .day, .hour, .minute, .second],
                from: alarm.fireAt
            )
            let trigger = UNCalendarNotificationTrigger(dateMatching: parts, repeats: false)
            let request = UNNotificationRequest(identifier: alarm.id, content: content, trigger: trigger)
            try? await center.add(request)
        }
    }

    private static let gate = ReminderGate()
}

/// Coalesces overlapping `enqueue` calls so an older wipe/re-add cannot
/// resurrect a completed or rescheduled reminder.
private actor ReminderGate {
    private var latest: (DeskSnapshot, Date)?
    private var running = false

    func enqueue(snapshot: DeskSnapshot, now: Date) {
        latest = (snapshot, now)
        guard !running else { return }
        running = true
        Task { await drain() }
    }

    private func drain() async {
        while let (snapshot, now) = latest {
            latest = nil
            await ReminderScheduler.sync(snapshot: snapshot, now: now)
        }
        running = false
    }
}
