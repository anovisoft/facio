import Foundation

enum SeedFactory {
    static func buildSeed(now: Date) throws -> DeskSnapshot {
        let pushCadence = try Cadence.of(count: 3, period: .week)
        let vegCadence = try Cadence.of(count: 1, period: .day)

        let subjects = [
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
        ]

        let cues = [
            CueLaw.addCue(
                id: "push-ups-brace",
                subjectId: "push-ups",
                kind: .correction,
                text: "держи корпус и ягодицы",
                surface: .doTime
            ),
        ]

        let instances = [
            Instance(id: "push-ups-open", subjectId: "push-ups", when: now, status: .prepared),
            Instance(id: "vegetables-open", subjectId: "vegetables", when: now, status: .prepared),
        ]

        let widgets = [
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

        return DeskSnapshot(subjects: subjects, cues: cues, instances: instances, widgets: widgets)
    }
}
