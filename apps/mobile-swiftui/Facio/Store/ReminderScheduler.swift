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

    /// How many days ahead alarms are laid down, today included.
    ///
    /// iOS keeps at most **64 pending local notifications per app** and drops
    /// the surplus without a word — an eighth hour, or a fourth practice, would
    /// silently cancel an alarm somebody is counting on. So the horizon is a
    /// few days and not a month: 7 hours × 30 days is 210 requests for one
    /// practice, which is the overflow rather than a schedule.
    ///
    /// Three is chosen because `enqueue` runs on every foreground and on every
    /// change of the desk, so the horizon only has to survive a stretch of the
    /// app not being opened at all — and a weekend is that stretch. One day
    /// would make the alarm depend on the person having already come back,
    /// which is the one thing a reminder cannot assume.
    static let horizonDays = 3

    /// The most alarms one sync will put up, out of the 64 the system keeps.
    ///
    /// Eight slots are left free on purpose: the pause check-ins ride in the
    /// same queue, and the margin is what keeps a busy desk from being the
    /// reason a notification is dropped. Over budget, the **nearest** alarms
    /// win — they are the ones due before the next foreground re-enqueues, and
    /// the far ones are rebuilt from the rhythm the moment it does.
    static let alarmBudget = 56

    static func alarmId(widgetId: String) -> String {
        idPrefix + widgetId
    }

    /// One id per hour of the window (Q34) and per day of the horizon (R20).
    ///
    /// Two hours on one practice are two alarms, so they cannot share an
    /// identifier — the second would silently overwrite the first in the
    /// notification centre; the same is true of the same hour on two days.
    ///
    /// **Today's ids are byte-identical to the ones this always wrote:** a
    /// single-hour window keeps the plain `reminder:{widgetId}`, several hours
    /// keep `…@{hour}`, and the day segment appears only on the days after
    /// today. Old pending requests are matched and cleared by the same strings
    /// they were added under.
    static func alarmId(widgetId: String, clock: ClockTime? = nil, on day: Date? = nil) -> String {
        var id = alarmId(widgetId: widgetId)
        if let clock { id += "@" + clock.shortLabel }
        if let day { id += "#" + SlotLaw.dayKey(day) }
        return id
    }

    static func checkInAlarmId(subjectId: String) -> String {
        idPrefix + "check-in:" + subjectId
    }

    private static let silentStatuses: Set<WidgetStatus> = [.done, .snoozed, .archived]

    /// Every alarm this desk should be holding right now.
    ///
    /// **The day comes from the rhythm, the hour from the window** (04:
    /// "deterministic, fired from the subject's cadence and window"). Before
    /// R20 the day came from `fire_at` on the widget — a stamp written when the
    /// reminder was created and moved by nobody afterwards — so a lone practice
    /// rang on the day it was made and went silent for good: every hour of a
    /// day already behind us is a moment in the past, and every moment in the
    /// past is dropped. Measured on a desk built on day N: one alarm on N, zero
    /// on N+1, N+2 and N+7.
    ///
    /// The days are `SlotLaw.dueDays` over the nearest `horizonDays` strips of
    /// the horizon the 7-day calendar already builds — a daily practice is owed
    /// something every day and rings every day, a `2×/week` one rings on the
    /// days the law counts as owed and falls silent once the week's count is
    /// met. No model is asked anything (06 AI #10); this is arithmetic.
    ///
    /// `fire_at` stays exactly what it was — the mark of the next fire — and is
    /// never rewritten backwards from here. It contributes one thing: a stamp
    /// pointing **past** the horizon still rings, because an hour a person set
    /// far ahead is theirs to keep.
    static func alarms(from snapshot: DeskSnapshot, now: Date) -> [ReminderAlarm] {
        let bySubject = Dictionary(uniqueKeysWithValues: snapshot.subjects.map { ($0.id, $0) })
        let today = SlotLaw.startOfDay(for: now)
        let strips = Array(SlotLaw.horizon(desk: snapshot, origin: now).days.prefix(horizonDays))
        var owedBySubject: [String: [Date]] = [:]

        var alarms: [ReminderAlarm] = snapshot.widgets.flatMap { widget -> [ReminderAlarm] in
            // Postponed (`snoozed`) and taken off the lid (`archived`) are both
            // "do not ask right now" — a widget that is not on the lid must not
            // ring from the pocket either.
            guard widget.type == .reminder, !silentStatuses.contains(widget.status) else { return [] }
            let subject = bySubject[widget.subjectId]
            if subject?.status == .retired || subject?.status == .paused {
                return []
            }
            guard let stamp = widget.reminderFireAt else { return [] }
            let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
            let cue = CueLaw.timingCue(in: snapshot.cues, subjectId: widget.subjectId)
            // Every hour the person named is its own alarm (Q34). Without a
            // window there is nothing but the hour already on the widget.
            let hours = subject?.window?.hours ?? [ReminderClock.clock(from: stamp)]
            let owed = owedBySubject[widget.subjectId]
                ?? SlotLaw.dueDays(subjectId: widget.subjectId, in: strips)
            owedBySubject[widget.subjectId] = owed

            return firingDays(owed: owed, stamp: stamp, today: today).flatMap { day -> [ReminderAlarm] in
                hours.compactMap { clock -> ReminderAlarm? in
                    let moment = ReminderClock.date(on: day, clock: clock)
                    guard moment > now else { return nil }
                    let deadline = DisplayCopy.succeedBy(clock: ReminderClock.clock(from: moment))
                    let body = [deadline, cue?.text].compactMap { $0 }.joined(separator: " · ")
                    return ReminderAlarm(
                        id: alarmId(
                            widgetId: widget.id,
                            clock: hours.count == 1 ? nil : clock,
                            on: day == today ? nil : day
                        ),
                        fireAt: moment,
                        title: title,
                        body: body.isEmpty ? title : body
                    )
                }
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
        return withinBudget(alarms)
    }

    /// The dates this widget rings on: what the law owes, plus a stamp set
    /// beyond the horizon.
    ///
    /// The stamp is admitted only when it points at a day **after** today.
    /// Today belongs to the rhythm alone — otherwise a practice whose count is
    /// already met would still ring because of a number written days ago, which
    /// is the stale stamp all over again.
    private static func firingDays(owed: [Date], stamp: Date, today: Date) -> [Date] {
        let stampDay = SlotLaw.startOfDay(for: stamp)
        guard stampDay > today, !owed.contains(stampDay) else { return owed }
        return (owed + [stampDay]).sorted()
    }

    /// Sorted by time, cut to `alarmBudget`.
    ///
    /// The system keeps 64 and silently discards the rest, so the cut is made
    /// here where it can be reasoned about instead of there where it cannot be
    /// seen. Nearest first: those are the alarms that fire before the next
    /// `enqueue` rebuilds the whole list anyway.
    private static func withinBudget(_ alarms: [ReminderAlarm]) -> [ReminderAlarm] {
        let sorted = alarms.sorted { lhs, rhs in
            if lhs.fireAt != rhs.fireAt { return lhs.fireAt < rhs.fireAt }
            return lhs.id < rhs.id
        }
        return Array(sorted.prefix(alarmBudget))
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
