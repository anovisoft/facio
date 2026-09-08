import Foundation

enum InstanceLaw {
    static func isDoneToday(_ widget: Widget, now: Date) -> Bool {
        guard widget.status == .done, let when = widget.when else { return false }
        return Calendar.current.isDate(when, inSameDayAs: now)
    }

    /// Whether the case under this widget belongs to a day already over (S5).
    ///
    /// A tile drawn on Today is not necessarily *about* today. An untouched
    /// daily tile keeps standing over the case it was written for, and on the
    /// next day it is yesterday's question still on the screen. Telling the two
    /// apart is the whole of «yesterday's miss stays yesterday's»: the case
    /// that never happened is left `prepared` on its own day, and the tile is
    /// rebound to ask about this one.
    ///
    /// Read from the **case**, never from the widget's own `when` — that field
    /// is the closing stamp and is nil while a tile is merely ready.
    static func standsOnAnEarlierDay(caseWhen: Date?, now: Date) -> Bool {
        guard let caseWhen else { return false }
        return SlotLaw.startOfDay(for: caseWhen) < SlotLaw.startOfDay(for: now)
    }

    /// Clone a new Today tile when the template still occupies Today:
    /// a live run, or a done-today tile that must stay dim until midnight.
    static func shouldClone(template: Widget, now: Date) -> Bool {
        if template.status == .running { return true }
        if isDoneToday(template, now: now) { return true }
        if template.section == .today, template.status == .ready { return true }
        return false
    }

    static func resetPayload(of widget: Widget, now: Date, window: TimeWindow?) -> WidgetPayload {
        switch widget.type {
        case .counter:
            return WidgetPayload(count: 0, target: widget.counterTarget)
        case .tick:
            return WidgetPayload(done: false)
        case .reminder:
            let fireAt = window.map { ReminderClock.reminderFireAt(window: $0, on: now) } ?? now
            return WidgetPayload(fireAt: fireAt)
        case .checklist, .timer, .stepper:
            return WidgetPayload()
        }
    }

    static func newWidget(
        from template: Widget,
        instanceId: String,
        payload: WidgetPayload,
        now: Date
    ) -> Widget {
        Widget(
            id: "w-\(instanceId)",
            type: template.type,
            title: template.title,
            payload: payload,
            status: .ready,
            when: payload.fireAt ?? now,
            section: .today,
            subjectId: template.subjectId,
            instanceId: instanceId,
            tileSize: template.tileSize,
            version: template.version
        )
    }

    static func rebind(
        _ widget: Widget,
        instanceId: String,
        payload: WidgetPayload,
        now: Date
    ) -> Widget {
        var next = widget
        next.instanceId = instanceId
        next.payload = payload
        next.status = .ready
        next.section = .today
        next.when = payload.fireAt ?? now
        return next
    }

    static func preferredLive(in widgets: [Widget], subjectId: String, now: Date) -> Widget? {
        let all = widgets.filter { $0.subjectId == subjectId && $0.type.showsOnLid }
        if let today = all.first(where: { $0.section == .today && $0.status != .done }) {
            return today
        }
        if let done = all.first(where: { isDoneToday($0, now: now) }) {
            return done
        }
        return all.first
    }

    static func sorted(_ instances: [Instance], subjectId: String) -> [Instance] {
        instances
            .filter { $0.subjectId == subjectId }
            .sorted { lhs, rhs in
                if lhs.when != rhs.when { return lhs.when < rhs.when }
                return lhs.id < rhs.id
            }
    }
}
