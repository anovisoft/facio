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

    /// One id per hour of the window (Q34). Two hours on one practice are two
    /// alarms, so they cannot share an identifier — the second would silently
    /// overwrite the first in the notification centre. A single-hour window
    /// keeps the plain id it always had.
    static func alarmId(widgetId: String, clock: ClockTime) -> String {
        alarmId(widgetId: widgetId) + "@" + clock.shortLabel
    }

    static func checkInAlarmId(subjectId: String) -> String {
        idPrefix + "check-in:" + subjectId
    }

    private static let silentStatuses: Set<WidgetStatus> = [.done, .snoozed, .archived]

    static func alarms(from snapshot: DeskSnapshot, now: Date) -> [ReminderAlarm] {
        let bySubject = Dictionary(uniqueKeysWithValues: snapshot.subjects.map { ($0.id, $0) })
        var alarms: [ReminderAlarm] = snapshot.widgets.flatMap { widget -> [ReminderAlarm] in
            // Postponed (`snoozed`) and taken off the lid (`archived`) are both
            // "do not ask right now" — a widget that is not on the lid must not
            // ring from the pocket either.
            guard widget.type == .reminder, !silentStatuses.contains(widget.status) else { return [] }
            let subject = bySubject[widget.subjectId]
            if subject?.status == .retired || subject?.status == .paused {
                return []
            }
            guard let fireAt = widget.reminderFireAt else { return [] }
            let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
            let cue = CueLaw.timingCue(in: snapshot.cues, subjectId: widget.subjectId)
            // Every hour the person named is its own alarm (Q34). Without a
            // window there is nothing but the hour already on the widget.
            let window = subject?.window
            let day = Calendar.current.startOfDay(for: fireAt)
            let moments: [(String, Date)] = window.map { window in
                ReminderClock.reminderFireTimes(window: window, on: day).enumerated().map { index, moment in
                    let clock = window.hours[index]
                    let id = window.hours.count == 1
                        ? alarmId(widgetId: widget.id)
                        : alarmId(widgetId: widget.id, clock: clock)
                    return (id, moment)
                }
            } ?? [(alarmId(widgetId: widget.id), fireAt)]
            return moments.compactMap { id, moment in
                guard moment > now else { return nil }
                let deadline = DisplayCopy.succeedBy(clock: ReminderClock.clock(from: moment))
                let body = [deadline, cue?.text].compactMap { $0 }.joined(separator: " · ")
                return ReminderAlarm(
                    id: id,
                    fireAt: moment,
                    title: title,
                    body: body.isEmpty ? title : body
                )
            }
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
