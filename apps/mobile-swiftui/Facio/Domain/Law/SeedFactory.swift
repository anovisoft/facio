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
    /// Two things it deliberately does not do. It never multiplies a reminder
    /// widget — the hours live in that subject's window, and a tile per hour
    /// would turn a window into a calendar. And it counts cases already closed,
    /// so ticking the first check does not write an eighth: the seventh check
    /// is the seventh case (04).
    ///
    /// **R19:** the day it tops up is today, every day. Yesterday is left
    /// exactly as yesterday ended it — no date is rewritten, no closed case is
    /// reopened, and a check that was missed stays missed on the day it was
    /// missed. A miss is a miss; the drift and the delta go on counting it.
    static func ensureOccurrences(in snapshot: DeskSnapshot, now: Date) -> DeskSnapshot {
        var next = snapshot
        for subject in snapshot.subjects {
            let missing = SlotLaw.occurrencesMissing(
                subject,
                instances: next.instances,
                widgets: next.widgets,
                on: now
            )
            if missing > 0, let template = occurrenceTemplate(in: next, subject: subject, now: now) {
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
            next = groupToday(subject: subject, in: next, now: now)
            next = rollAlarm(subject: subject, in: next, now: now)
        }
        return next
    }

    /// Q34 after the first day on a phone: the occurrences of one subject
    /// inside one period share a **`group_id`** and the lid draws them once.
    ///
    /// Two writes, both derived, both idempotent. The `group_id` is the subject
    /// and the day, so running this twice re-stamps instead of splitting. And
    /// the hours the person named are laid onto the cases in order, so a check
    /// carries the hour it is for — without that, seven cases are seven
    /// identical squares and «отметить именно проверку в 15:00» is a guess.
    ///
    /// The hours are distributed **only** when there are exactly as many of
    /// them as there are occurrences. Fewer hours than checks would mean us
    /// deciding which check happens when, and nothing here invents an hour the
    /// person did not say (Q34).
    ///
    /// A practice that promises one a day is not touched at all: no `group_id`,
    /// one tile, exactly as before — which is also why an old desk opens.
    private static func groupToday(subject: Subject, in snapshot: DeskSnapshot, now: Date) -> DeskSnapshot {
        guard SlotLaw.occurrencesPromised(subject) > 1 else { return snapshot }
        var next = snapshot
        let hourCases = SlotLaw.hourInstanceIds(subjectId: subject.id, widgets: next.widgets)
        let today = Set(
            next.instances
                .filter {
                    $0.subjectId == subject.id
                        && SlotLaw.isSameDay($0.when, now)
                        && !hourCases.contains($0.id)
                }
                .map(\.id)
        )
        guard today.count > 1 else { return snapshot }

        var whenOf: [String: Date] = [:]
        for instance in next.instances { whenOf[instance.id] = instance.when }
        let ordered = next.widgets
            .filter { today.contains($0.instanceId) && $0.type.showsOnLid && $0.status != .archived }
            .sorted { lhs, rhs in
                let left = whenOf[lhs.instanceId] ?? now
                let right = whenOf[rhs.instanceId] ?? now
                if left != right { return left < right }
                return lhs.id < rhs.id
            }
        guard ordered.count > 1 else { return snapshot }

        let groupId = GroupLaw.key(subjectId: subject.id, day: now)
        let hours = subject.window?.hours ?? []
        let laysHours = hours.count == ordered.count
        for (position, widget) in ordered.enumerated() {
            guard let index = next.widgets.firstIndex(where: { $0.id == widget.id }) else { continue }
            next.widgets[index].groupId = groupId
            guard laysHours else { continue }
            let at = ReminderClock.date(on: now, clock: hours[position])
            // A closed check keeps the moment it was closed on its widget —
            // that stamp is what holds a done tile on Today until midnight.
            if next.widgets[index].status != .done {
                next.widgets[index].when = at
            }
            if let caseIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[caseIndex].when = at
            }
        }
        return next
    }

    /// The thing the person ticks, on today's case. A reminder is the hour, not
    /// the check, so it is never the template.
    ///
    /// **R19 — the template outlives the day.** Looking only at today's cases
    /// is what made the whole construction last exactly one day: a fresh day
    /// owns no case yet, so there was no template, so the top-up wrote nothing
    /// and the practice simply never came back (measured on R18). The face of a
    /// practice does not belong to a date, so when today has nothing to copy the
    /// freshest check of any day is copied instead — and only its **face**:
    /// `InstanceLaw.resetPayload` hands the new day an empty tick, so nothing of
    /// yesterday's state rides along (P11: instances end, subjects do not).
    ///
    /// The carry-over is offered **only to a practice that promises more than
    /// one a day**. A daily tick and a weekly ride come back by rebinding the
    /// standing widget onto a new case, which is a mechanism of their own;
    /// copying for them would leave two tiles of one practice on the lid and
    /// change a desk written before Q34.
    private static func occurrenceTemplate(in snapshot: DeskSnapshot, subject: Subject, now: Date) -> Widget? {
        let candidates = snapshot.widgets.filter { widget in
            widget.subjectId == subject.id
                && widget.type != .reminder
                && widget.type.showsOnLid
                && widget.status != .archived
        }
        let today = Set(
            snapshot.instances
                .filter { $0.subjectId == subject.id && SlotLaw.isSameDay($0.when, now) }
                .map(\.id)
        )
        if let standing = candidates.first(where: { today.contains($0.instanceId) }) { return standing }
        guard SlotLaw.occurrencesPromised(subject) > 1 else { return nil }

        var whenOf: [String: Date] = [:]
        for instance in snapshot.instances { whenOf[instance.id] = instance.when }
        return candidates.max { lhs, rhs in
            let left = whenOf[lhs.instanceId] ?? .distantPast
            let right = whenOf[rhs.instanceId] ?? .distantPast
            if left != right { return left < right }
            return lhs.id < rhs.id
        }
    }

    /// The alarms of the new day stand on the new day's hours (R19).
    ///
    /// `ReminderScheduler` lays the window onto the date its widget carries, and
    /// drops every moment already behind us. So a reminder still stamped with
    /// yesterday puts up nothing at all: the seven hours are seven times in the
    /// past. Moving the stamp forward is not a new hour and not a new promise —
    /// the hours are read from the same window they always were.
    ///
    /// Only a practice whose day this top-up rolls, and only a stamp that is
    /// already behind: an alarm somebody set ahead is theirs, not ours.
    private static func rollAlarm(subject: Subject, in snapshot: DeskSnapshot, now: Date) -> DeskSnapshot {
        guard SlotLaw.occurrencesPromised(subject) > 1,
              let window = snapshot.subjects.first(where: { $0.id == subject.id })?.window
        else { return snapshot }
        var next = snapshot
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
        for index in next.widgets.indices {
            let widget = next.widgets[index]
            guard widget.subjectId == subject.id,
                  widget.type == .reminder,
                  widget.status != .archived,
                  let standing = widget.reminderFireAt,
                  standing < now,
                  !SlotLaw.isSameDay(standing, now)
            else { continue }
            next.widgets[index].payload.fireAt = fireAt
            next.widgets[index].when = fireAt
            if let caseIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }),
               next.instances[caseIndex].status != .completed
            {
                next.instances[caseIndex].when = fireAt
            }
        }
        return next
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