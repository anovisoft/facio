import Foundation
import Observation

@Observable
@MainActor
final class DeskStore {
    private(set) var snapshot: DeskSnapshot
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
            snapshot = loaded
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

    func widget(id: String) -> Widget? {
        snapshot.widgets.first { $0.id == id }
    }

    func markCueSurfaced(widgetId: String, place: String) {
        guard let widget = widget(id: widgetId),
              let cue = cueFor(subjectId: widget.subjectId),
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
        try? repository.saveSnapshot(snapshot)
    }
}
