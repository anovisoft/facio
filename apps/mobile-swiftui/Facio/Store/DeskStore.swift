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
            let migrated = try SeedFactory.ensureFounding(in: loaded, now: now())
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
            widgets: snapshot.widgets,
            histories: snapshot.driftAsks
        )
    }

    func subject(id: String) -> Subject? {
        snapshot.subjects.first { $0.id == id }
    }

    func showsOnLid(subjectId: String) -> Bool {
        subject(id: subjectId)?.status != .retired
    }

    func surfaces(_ card: DriftCard) -> Bool {
        guard let subject = subject(id: card.subjectId) else { return false }
        return DriftLaw.shouldSurface(
            card,
            askedAt: snapshot.driftAskedAt[card.subjectId],
            cadence: subject.cadence,
            now: now()
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

    func widget(instanceId: String) -> Widget? {
        snapshot.widgets.first { $0.instanceId == instanceId }
    }

    func instances(for subjectId: String) -> [Instance] {
        InstanceLaw.sorted(snapshot.instances, subjectId: subjectId)
    }

    func preferredInstanceId(subjectId: String) -> String? {
        if let live = templateWidget(subjectId: subjectId) {
            return live.instanceId
        }
        return instances(for: subjectId).last?.id
    }

    @discardableResult
    func addInstance(subjectId: String) -> String? {
        guard subject(id: subjectId) != nil else { return nil }
        guard let template = templateWidget(subjectId: subjectId) else { return nil }
        let stamp = now()
        let instanceId = "\(subjectId)-\(UUID().uuidString)"
        let payload = InstanceLaw.resetPayload(
            of: template,
            now: stamp,
            window: windowFor(subjectId: subjectId)
        )
        let clone = InstanceLaw.shouldClone(template: template, now: stamp)
        commit(reminders: template.type == .reminder) { next in
            next.instances.append(Instance(id: instanceId, subjectId: subjectId, when: stamp, status: .prepared))
            if let subjectIndex = next.subjects.firstIndex(where: { $0.id == subjectId }) {
                next.subjects[subjectIndex].instanceIds.append(instanceId)
            }
            if clone {
                next.widgets.append(InstanceLaw.newWidget(from: template, instanceId: instanceId, payload: payload, now: stamp))
            } else if let widgetIndex = next.widgets.firstIndex(where: { $0.id == template.id }) {
                next.widgets[widgetIndex] = InstanceLaw.rebind(
                    next.widgets[widgetIndex],
                    instanceId: instanceId,
                    payload: payload,
                    now: stamp
                )
            }
        }
        return instanceId
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

    func answerDrift(subjectId: String, offer: DriftOffer) {
        guard let card = lid.driftCard, card.subjectId == subjectId, surfaces(card) else { return }
        switch offer {
        case .moveToToday:
            applyDrift(subjectId: subjectId, offer: offer, reminders: true) { next in
                moveToToday(subjectId, in: &next)
            }
        case .onceAWeek:
            applyDrift(subjectId: subjectId, offer: offer, reminders: false) { next in
                shrinkToOnceAWeek(subjectId, in: &next)
            }
        case .retire:
            applyDrift(subjectId: subjectId, offer: offer, reminders: true) { next in
                retireSubject(subjectId, in: &next)
            }
        case .stop:
            return
        }
    }

    func applyTalk(_ desk: DeskSnapshot) {
        let previous = snapshot
        let written = desk.cues.filter { incoming in
            previous.cues.first { $0.id == incoming.id } != incoming
        }
        commit(reminders: true) { next in
            next = desk
        }
        for cue in written {
            journal(.cueWritten, subjectId: cue.subjectId, cueId: cue.id, payload: ["text": cue.text])
        }
        for subject in desk.subjects {
            let before = previous.subjects.first { $0.id == subject.id }
            if subject.status == .shrunk, before?.status != .shrunk {
                journal(.subjectShrunk, subjectId: subject.id)
            }
            if subject.status == .retired, before?.status != .retired {
                journal(.subjectRetired, subjectId: subject.id)
            }
        }
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

    private func templateWidget(subjectId: String) -> Widget? {
        let all = snapshot.widgets.filter { $0.subjectId == subjectId && $0.type.showsOnLid }
        if let live = all.first(where: { $0.section == .today && $0.status != .done }) { return live }
        if let doneToday = all.first(where: { InstanceLaw.isDoneToday($0, now: now()) }) { return doneToday }
        return all.first
    }

    private func applyDrift(
        subjectId: String,
        offer: DriftOffer,
        reminders: Bool,
        body: (inout DeskSnapshot) -> Void
    ) {
        let stamp = now()
        commit(reminders: reminders) { next in
            body(&next)
            var state = next.driftAsks[subjectId] ?? DriftAskState()
            state.asksMade += 1
            next.driftAsks[subjectId] = state
            next.driftAskedAt[subjectId] = stamp
        }
        journal(
            .driftAnswered,
            subjectId: subjectId,
            payload: ["offer": offer.rawValue]
        )
        if offer == .onceAWeek {
            journal(.subjectShrunk, subjectId: subjectId, payload: ["cadence": "1/week"])
        }
        if offer == .retire {
            journal(.subjectRetired, subjectId: subjectId)
        }
    }

    private func moveToToday(_ subjectId: String, in next: inout DeskSnapshot) {
        let stamp = now()
        let window = next.subjects.first { $0.id == subjectId }?.window
        for index in next.widgets.indices where next.widgets[index].subjectId == subjectId {
            next.widgets[index].section = .today
            guard next.widgets[index].type == .reminder, let window else { continue }
            let fireAt = ReminderClock.reminderFireAt(window: window, on: stamp)
            next.widgets[index].payload.fireAt = fireAt
            next.widgets[index].when = fireAt
            let instanceId = next.widgets[index].instanceId
            guard let instanceIndex = next.instances.firstIndex(where: { $0.id == instanceId }) else { continue }
            if next.instances[instanceIndex].status == .completed {
                let freshId = "\(subjectId)-open-\(UUID().uuidString)"
                next.instances.append(Instance(id: freshId, subjectId: subjectId, when: fireAt, status: .prepared))
                if let subjectIndex = next.subjects.firstIndex(where: { $0.id == subjectId }) {
                    next.subjects[subjectIndex].instanceIds.append(freshId)
                }
                next.widgets[index].instanceId = freshId
                next.widgets[index].status = .ready
            } else {
                next.instances[instanceIndex].when = fireAt
            }
        }
    }

    private func shrinkToOnceAWeek(_ subjectId: String, in next: inout DeskSnapshot) {
        guard let weekly = try? Cadence.of(count: 1, period: .week) else { return }
        guard let index = next.subjects.firstIndex(where: { $0.id == subjectId }) else { return }
        var subject = SubjectLaw.shrink(next.subjects[index])
        subject.cadence = weekly
        next.subjects[index] = subject
    }

    private func retireSubject(_ subjectId: String, in next: inout DeskSnapshot) {
        guard let index = next.subjects.firstIndex(where: { $0.id == subjectId }) else { return }
        next.subjects[index] = SubjectLaw.retire(next.subjects[index])
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
