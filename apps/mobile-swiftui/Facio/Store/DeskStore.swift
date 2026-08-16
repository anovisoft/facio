import Foundation
import Observation

@Observable
@MainActor
final class DeskStore {
    private(set) var snapshot: DeskSnapshot
    private let repository: DeskRepository
    private let now: () -> Date
    private var surfacedDay = Date.distantPast
    private var surfacedPlaces: Set<String> = []

    static func live() -> DeskStore {
        do {
            return try DeskStore(repository: try DeskRepository.applicationSupport())
        } catch {
            fatalError("desk warehouse failed: \(error)")
        }
    }

    init(repository: DeskRepository, now: @escaping () -> Date = Date.init) throws {
        self.repository = repository
        self.now = now
        if let loaded = try repository.loadSnapshot() {
            let migrated = try SeedFactory.ensureBike(in: loaded, now: now())
            snapshot = migrated
            if migrated != loaded {
                try repository.saveSnapshot(migrated)
            }
        } else {
            snapshot = try SeedFactory.buildSeed(now: now())
            try repository.saveSnapshot(snapshot)
        }
        let day = Calendar.current.startOfDay(for: now())
        surfacedDay = day
        surfacedPlaces = repository.surfacedPlaces(on: day)
    }

    var lid: LidProjection {
        LidProjectionLaw.project(
            now: now(),
            subjects: snapshot.subjects,
            instances: snapshot.instances,
            widgets: snapshot.widgets
        )
    }

    func cueFor(subjectId: String) -> Cue? {
        CueLaw.doTimeCue(in: snapshot.cues, subjectId: subjectId)
    }

    func surfaceCue(for widget: Widget) -> Cue? {
        CueLaw.surfaceCue(in: snapshot.cues, subjectId: widget.subjectId, widgetType: widget.type)
    }

    func windowFor(subjectId: String) -> TimeWindow? {
        snapshot.subjects.first { $0.id == subjectId }?.window
    }

    func widget(id: String) -> Widget? {
        snapshot.widgets.first { $0.id == id }
    }

    func markCueSurfaced(widgetId: String, place: String) {
        guard let widget = widget(id: widgetId),
              let cue = surfaceCue(for: widget),
              widget.status != .done
        else { return }
        let day = Calendar.current.startOfDay(for: now())
        if day != surfacedDay {
            surfacedDay = day
            surfacedPlaces = repository.surfacedPlaces(on: day)
        }
        let key = "\(widgetId)|\(place)"
        guard surfacedPlaces.insert(key).inserted else { return }
        commit { next in
            guard let index = next.cues.firstIndex(where: { $0.id == cue.id }) else { return }
            next.cues[index].hits.surfaced += 1
        }
        journal(
            .cueSurfaced,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            cueId: cue.id,
            payload: ["place": place]
        )
    }

    func tickCounter(widgetId: String, delta: Int) {
        guard let widget = widget(id: widgetId), widget.type == .counter else { return }
        let nextCount = max(0, widget.counterCount + delta)
        let wasDone = widget.status == .done
        let wasReady = widget.status == .ready
        commit { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].payload.count = nextCount
            if wasDone || wasReady {
                next.widgets[index].status = .running
                if wasDone { next.widgets[index].when = nil }
            }
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }),
               wasDone || wasReady
            {
                next.instances[instanceIndex].status = .inProgress
            }
        }
        if wasReady {
            journal(.instanceStarted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        }
        journal(
            .counterTicked,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: ["count": String(nextCount)]
        )
    }

    func completeCounter(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .counter, widget.status != .done else { return }
        let stamp = now()
        let cue = cueFor(subjectId: widget.subjectId)
        commit { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].status = .done
            next.widgets[index].when = stamp
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[instanceIndex].status = .completed
                next.instances[instanceIndex].when = stamp
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
    }

    func toggleTick(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .tick else { return }
        let stamp = now()
        let makingDone = widget.status != .done
        commit { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].payload.done = makingDone
            next.widgets[index].status = makingDone ? .done : .ready
            next.widgets[index].when = makingDone ? stamp : nil
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[instanceIndex].status = makingDone ? .completed : .prepared
                next.instances[instanceIndex].when = stamp
            }
        }
        journal(
            .tickToggled,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: ["done": makingDone ? "true" : "false"]
        )
        if makingDone {
            journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        }
    }

    func editReminderLatestBy(widgetId: String, latestBy: ClockTime) {
        guard let widget = widget(id: widgetId), widget.type == .reminder else { return }
        guard let window = windowFor(subjectId: widget.subjectId) else { return }
        let clock = ReminderClock.clamp(latestBy, to: window)
        let day = Calendar.current.startOfDay(for: widget.reminderFireAt ?? now())
        let fireAt = ReminderClock.date(on: day, clock: clock)
        commit(reminders: true) { next in
            guard let widgetIndex = next.widgets.firstIndex(where: { $0.id == widgetId }),
                  let subjectIndex = next.subjects.firstIndex(where: { $0.id == widget.subjectId }),
                  var nextWindow = next.subjects[subjectIndex].window
            else { return }
            nextWindow.latestBy = clock
            next.subjects[subjectIndex].window = nextWindow
            next.widgets[widgetIndex].payload.fireAt = fireAt
            next.widgets[widgetIndex].when = fireAt
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }),
               next.instances[instanceIndex].status != .completed
            {
                next.instances[instanceIndex].when = fireAt
            }
        }
    }

    func completeReminder(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .reminder, widget.status != .done else { return }
        let stamp = now()
        let cue = surfaceCue(for: widget)
        commit(reminders: true) { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].status = .done
            next.widgets[index].when = stamp
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[instanceIndex].status = .completed
                next.instances[instanceIndex].when = stamp
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
    }

    func editCueText(cueId: String, text: String) {
        commit { next in
            guard let index = next.cues.firstIndex(where: { $0.id == cueId }) else { return }
            next.cues[index].text = text
        }
        journal(.cueWritten, cueId: cueId, payload: ["text": text])
    }

    func editTarget(widgetId: String, goal: Int) {
        guard let widget = widget(id: widgetId) else { return }
        commit { next in
            guard let widgetIndex = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[widgetIndex].payload.target = goal
            if let subjectIndex = next.subjects.firstIndex(where: { $0.id == widget.subjectId }) {
                let current = next.subjects[subjectIndex].target?.current ?? next.widgets[widgetIndex].counterCount
                next.subjects[subjectIndex].target = Target(current: current, goal: goal)
            }
        }
    }

    private func commit(reminders: Bool = false, _ body: (inout DeskSnapshot) -> Void) {
        var next = snapshot
        body(&next)
        guard next != snapshot else { return }
        snapshot = next
        try? repository.saveSnapshot(next)
        if reminders {
            ReminderScheduler.enqueue(snapshot: next, now: now())
        }
    }

    private func journal(
        _ type: JournalEventType,
        subjectId: String? = nil,
        widgetId: String? = nil,
        instanceId: String? = nil,
        cueId: String? = nil,
        payload: [String: String]? = nil
    ) {
        let event = JournalEvent(
            id: UUID().uuidString,
            type: type,
            at: now(),
            subjectId: subjectId,
            widgetId: widgetId,
            instanceId: instanceId,
            cueId: cueId,
            payload: payload
        )
        try? repository.append(event)
    }
}
