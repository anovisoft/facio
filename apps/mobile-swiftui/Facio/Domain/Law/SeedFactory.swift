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
        return try ensureBike(in: snapshot, now: now)
    }

    static func ensureBike(in snapshot: DeskSnapshot, now: Date) throws -> DeskSnapshot {
        var next = snapshot
        let window = ReminderClock.windowFromClosing(ClockTime(hour: 22, minute: 0))
        let fireAt = ReminderClock.reminderFireAt(window: window, on: now)
        let cadence = try Cadence.of(count: 2, period: .week)

        if !next.subjects.contains(where: { $0.id == "bike" }) {
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

        if let index = next.widgets.firstIndex(where: { $0.id == "bike-reminder" }) {
            if next.widgets[index].tileSize != .wide {
                next.widgets[index].tileSize = .wide
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
}