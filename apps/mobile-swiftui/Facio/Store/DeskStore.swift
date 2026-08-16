import Foundation
import Observation

@Observable
@MainActor
final class DeskStore {
    private(set) var snapshot: DeskSnapshot
    private(set) var generation = 0
    private let repository: DeskRepository
    private let now: () -> Date

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
        mutateCue(id: cue.id) { $0.hits.surfaced += 1 }
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
        guard var widget = widget(id: widgetId), widget.type == .counter else { return }
        let next = max(0, (widget.payload.count ?? 0) + delta)
        widget.payload.count = next
        if widget.status == .done {
            widget.status = .running
            widget.when = nil
            setInstance(id: widget.instanceId) { $0.status = .inProgress }
        } else if widget.status == .ready {
            widget.status = .running
            setInstance(id: widget.instanceId) { $0.status = .inProgress }
            journal(.instanceStarted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        }
        replace(widget)
        journal(
            .counterTicked,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: ["count": String(next)]
        )
    }

    func completeCounter(widgetId: String) {
        guard var widget = widget(id: widgetId), widget.type == .counter, widget.status != .done else { return }
        let stamp = now()
        widget.status = .done
        widget.when = stamp
        replace(widget)
        setInstance(id: widget.instanceId) { instance in
            instance.status = .completed
            instance.when = stamp
        }
        if let cue = cueFor(subjectId: widget.subjectId) {
            mutateCue(id: cue.id) { $0.hits.applied += 1 }
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
    }

    func toggleTick(widgetId: String) {
        guard var widget = widget(id: widgetId), widget.type == .tick else { return }
        let stamp = now()
        let makingDone = widget.status != .done
        widget.payload.done = makingDone
        widget.status = makingDone ? .done : .ready
        widget.when = makingDone ? stamp : nil
        replace(widget)
        setInstance(id: widget.instanceId) { instance in
            instance.status = makingDone ? .completed : .prepared
            instance.when = stamp
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
        guard let widgetIndex = snapshot.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
        var widget = snapshot.widgets[widgetIndex]
        guard widget.type == .reminder else { return }
        guard let subjectIndex = snapshot.subjects.firstIndex(where: { $0.id == widget.subjectId }),
              var window = snapshot.subjects[subjectIndex].window
        else { return }
        let clock = ReminderClock.clamp(latestBy, to: window)
        window.latestBy = clock
        let day = Calendar.current.startOfDay(for: widget.payload.fireAt ?? widget.when ?? now())
        let fireAt = ReminderClock.date(on: day, clock: clock)
        widget.payload.fireAt = fireAt
        widget.when = fireAt
        var next = snapshot
        next.subjects[subjectIndex].window = window
        next.widgets[widgetIndex] = widget
        if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }),
           next.instances[instanceIndex].status != .completed
        {
            next.instances[instanceIndex].when = fireAt
        }
        snapshot = next
        persist()
    }

    func completeReminder(widgetId: String) {
        guard var widget = widget(id: widgetId), widget.type == .reminder, widget.status != .done else { return }
        let stamp = now()
        widget.status = .done
        widget.when = stamp
        replace(widget)
        setInstance(id: widget.instanceId) { instance in
            instance.status = .completed
            instance.when = stamp
        }
        if let cue = surfaceCue(for: widget) {
            mutateCue(id: cue.id) { $0.hits.applied += 1 }
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
    }

    func editCueText(cueId: String, text: String) {
        mutateCue(id: cueId) { $0.text = text }
        journal(.cueWritten, cueId: cueId, payload: ["text": text])
    }

    func editTarget(widgetId: String, goal: Int) {
        guard var widget = widget(id: widgetId) else { return }
        widget.payload.target = goal
        replace(widget)
        if let index = snapshot.subjects.firstIndex(where: { $0.id == widget.subjectId }) {
            var subject = snapshot.subjects[index]
            let current = subject.target?.current ?? widget.payload.count ?? 0
            subject.target = Target(current: current, goal: goal)
            snapshot.subjects[index] = subject
        }
        persist()
    }

    private func replace(_ widget: Widget) {
        guard let index = snapshot.widgets.firstIndex(where: { $0.id == widget.id }) else { return }
        snapshot.widgets[index] = widget
        persist()
    }

    private func mutateCue(id: String, _ body: (inout Cue) -> Void) {
        guard let index = snapshot.cues.firstIndex(where: { $0.id == id }) else { return }
        body(&snapshot.cues[index])
        persist()
    }

    private func setInstance(id: String, _ body: (inout Instance) -> Void) {
        guard let index = snapshot.instances.firstIndex(where: { $0.id == id }) else { return }
        body(&snapshot.instances[index])
        persist()
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

    private func persist() {
        generation += 1
        try? repository.saveSnapshot(snapshot)
        ReminderScheduler.enqueue(snapshot: snapshot, now: now())
    }
}
