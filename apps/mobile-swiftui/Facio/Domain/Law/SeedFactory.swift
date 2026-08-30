import Foundation

enum SeedFactory {
    static func buildSeed(now: Date) throws -> DeskSnapshot {
        let pushCadence = try Cadence.of(count: 3, period: .week)
        let vegCadence = try Cadence.of(count: 1, period: .day)

        let snapshot = DeskSnapshot(
            subjects: [
                Subject(
                    id: "push-ups",
                    title: "push-ups",
                    cadence: pushCadence,
                    cueIds: ["push-ups-brace"],
                    target: Target(current: 28, goal: 30),
                    instanceIds: ["push-ups-open"]
                ),
                Subject(
                    id: "vegetables",
                    title: "vegetables",
                    cadence: vegCadence,
                    instanceIds: ["vegetables-open"]
                ),
            ],
            cues: [
                CueLaw.addCue(
                    id: "push-ups-brace",
                    subjectId: "push-ups",
                    kind: .correction,
                    text: "держи корпус и ягодицы",
                    surface: .doTime
                ),
            ],
            instances: [
                Instance(id: "push-ups-open", subjectId: "push-ups", when: now, status: .prepared),
                Instance(id: "vegetables-open", subjectId: "vegetables", when: now, status: .prepared),
            ],
            widgets: [
                Widget(
                    id: "push-ups-counter",
                    type: .counter,
                    title: "push-ups",
                    payload: WidgetPayload(count: 28, target: 30),
                    status: .ready,
                    section: .today,
                    subjectId: "push-ups",
                    instanceId: "push-ups-open",
                    tileSize: .compact
                ),
                Widget(
                    id: "vegetables-tick",
                    type: .tick,
                    title: "vegetables",
                    payload: WidgetPayload(done: false),
                    status: .ready,
                    section: .today,
                    subjectId: "vegetables",
                    instanceId: "vegetables-open",
                    tileSize: .compact
                ),
            ]
        )
        return try ensureFounding(in: snapshot, now: now)
    }

    static func ensureFounding(in snapshot: DeskSnapshot, now: Date) throws -> DeskSnapshot {
        try ensureDrift(in: try ensureBike(in: snapshot, now: now), now: now)
    }

    /// Q34: a practice that promised N times today gets N cases today.
    ///
    /// The law says how many are missing (`SlotLaw.occurrencesMissing`); this
    /// is the hand that writes them, at the one seam that already tops up a
    /// desk when the lid opens. No second mechanism and no scheduler: a case
    /// is only ever missing because a day started.
    ///
    /// Two things it deliberately does not do. It never touches a reminder
    /// widget — the hours live in that subject's window, and multiplying the
    /// tile would turn a window into a calendar. And it counts cases already
    /// closed, so ticking the first check does not write an eighth: the
    /// seventh check is the seventh case (04).
    static func ensureOccurrences(in snapshot: DeskSnapshot, now: Date) -> DeskSnapshot {
        var next = snapshot
        for subject in snapshot.subjects {
            let missing = SlotLaw.occurrencesMissing(
                subject,
                instances: next.instances,
                widgets: next.widgets,
                on: now
            )
            guard missing > 0, let template = occurrenceTemplate(in: next, subjectId: subject.id, now: now) else {
                continue
            }
            for _ in 0..<missing {
                let instanceId = "\(subject.id)-\(UUID().uuidString)"
                let payload = InstanceLaw.resetPayload(of: template, now: now, window: subject.window)
                next.instances.append(
                    Instance(id: instanceId, subjectId: subject.id, when: now, status: .prepared)
                )
                if let index = next.subjects.firstIndex(where: { $0.id == subject.id }) {
                    next.subjects[index].instanceIds.append(instanceId)
                }
                next.widgets.append(
                    InstanceLaw.newWidget(from: template, instanceId: instanceId, payload: payload, now: now)
                )
            }
        }
        return next
    }

    /// The thing the person ticks, on today's case. A reminder is the hour, not
    /// the check, so it is never the template.
    private static func occurrenceTemplate(in snapshot: DeskSnapshot, subjectId: String, now: Date) -> Widget? {
        let today = Set(
            snapshot.instances
                .filter { $0.subjectId == subjectId && SlotLaw.isSameDay($0.when, now) }
                .map(\.id)
        )
        return snapshot.widgets.first { widget in
            widget.subjectId == subjectId
                && widget.type != .reminder
                && widget.type.showsOnLid
                && widget.status != .archived
                && today.contains(widget.instanceId)
        }
    }

    static func ensureBike(in snapshot: DeskSnapshot, now: Date) throws -> DeskSnapshot {
        var next = snapshot
        let window = ReminderClock.windowFromClosing(ClockTime(hour: 22, minute: 0))
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
        let cadence = try Cadence.of(count: 2, period: .week)

        var backfilledWindow = false
        if let index = next.subjects.firstIndex(where: { $0.id == "bike" }) {
            if next.subjects[index].window == nil {
                next.subjects[index].window = window
                backfilledWindow = true
            }
        } else {
            next.subjects.append(
                Subject(
                    id: "bike",
                    title: "exercise bike",
                    cadence: cadence,
                    window: window,
                    cueIds: ["bike-gym-hours"],
                    instanceIds: ["bike-open"]
                )
            )
        }

        if !next.cues.contains(where: { $0.id == "bike-gym-hours" }) {
            next.cues.append(
                CueLaw.addCue(
                    id: "bike-gym-hours",
                    subjectId: "bike",
                    kind: .correction,
                    text: "зал до 22",
                    surface: .timing
                )
            )
        }

        if !next.instances.contains(where: { $0.id == "bike-open" }) {
            next.instances.append(Instance(id: "bike-open", subjectId: "bike", when: fireAt, status: .prepared))
        }

        if backfilledWindow,
           let instanceIndex = next.instances.firstIndex(where: { $0.id == "bike-open" }),
           next.instances[instanceIndex].status != .completed
        {
            next.instances[instanceIndex].when = fireAt
        }

        if let index = next.widgets.firstIndex(where: { $0.id == "bike-reminder" }) {
            if next.widgets[index].tileSize != .wide {
                next.widgets[index].tileSize = .wide
            }
            if backfilledWindow {
                next.widgets[index].payload.fireAt = fireAt
                next.widgets[index].when = fireAt
            }
        } else {
            next.widgets.append(
                Widget(
                    id: "bike-reminder",
                    type: .reminder,
                    title: "exercise bike",
                    payload: WidgetPayload(fireAt: fireAt),
                    status: .ready,
                    when: fireAt,
                    section: .today,
                    subjectId: "bike",
                    instanceId: "bike-open",
                    tileSize: .wide
                )
            )
        }

        return next
    }

    /// Founding silence: a weekly bike with no done instance is not drift.
    /// One completed ride 21 days ago + the live tile off Today makes the card.
    static func ensureDrift(in snapshot: DeskSnapshot, now: Date) throws -> DeskSnapshot {
        var next = snapshot
        guard let subjectIndex = next.subjects.firstIndex(where: { $0.id == "bike" }) else { return next }
        if next.subjects[subjectIndex].status == .retired { return next }

        let hasActivity = next.instances.contains {
            $0.subjectId == "bike" && ($0.status == .completed || $0.status == .inProgress)
        }
        guard !hasActivity else { return next }

        let silentAt = silenceStamp(now: now)
        if !next.instances.contains(where: { $0.id == "bike-silent" }) {
            next.instances.append(
                Instance(id: "bike-silent", subjectId: "bike", when: silentAt, status: .completed)
            )
        }
        if !next.subjects[subjectIndex].instanceIds.contains("bike-silent") {
            next.subjects[subjectIndex].instanceIds.append("bike-silent")
        }
        if let widgetIndex = next.widgets.firstIndex(where: { $0.id == "bike-reminder" }),
           next.widgets[widgetIndex].section == .today,
           next.widgets[widgetIndex].status != .done
        {
            next.widgets[widgetIndex].section = .lifetime
        }
        return next
    }

    private static func silenceStamp(now: Date) -> Date {
        let calendar = Calendar.current
        let day = calendar.date(byAdding: .day, value: -21, to: now) ?? now
        var parts = calendar.dateComponents([.year, .month, .day], from: day)
        parts.hour = 18
        parts.minute = 0
        parts.second = 0
        return calendar.date(from: parts) ?? day
    }
}