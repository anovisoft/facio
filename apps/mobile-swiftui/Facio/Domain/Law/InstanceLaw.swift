import Foundation

enum InstanceLaw {
    static func isDoneToday(_ widget: Widget, now: Date) -> Bool {
        guard widget.status == .done, let when = widget.when else { return false }
        return Calendar.current.isDate(when, inSameDayAs: now)
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

    static func sorted(_ instances: [Instance], subjectId: String) -> [Instance] {
        instances
            .filter { $0.subjectId == subjectId }
            .sorted { lhs, rhs in
                if lhs.when != rhs.when { return lhs.when < rhs.when }
                return lhs.id < rhs.id
            }
    }
}
