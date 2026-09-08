import Foundation
import Observation

@Observable
@MainActor
final class DeskStore {
    private(set) var snapshot: DeskSnapshot
    /// Day zero is over the moment the desk holds its first subject, and it
    /// never starts again. Read from disk at launch so relaunching an empty
    /// day does not bring the chips back.
    private(set) var dayZeroClosed: Bool
    /// The subject whose one clarity check (Q32) is due right now, or nothing.
    /// Set when a first case closes on a practice the mouth explained; cleared
    /// the moment the ask is shown, so it is shown once and never again.
    private(set) var clarificationAsk: String?
    /// The last talk turn that changed the desk, and the desk it changed — the
    /// one step back P6 requires. One record, never a stack: a newer changing
    /// turn takes the offer from the older one.
    private(set) var undoableTurn: UndoableTurn?
    private let repository: DeskRepository
    private let now: () -> Date
    private var surfacedDay = Date.distantPast
    private var surfacedPlaces: Set<String> = []
    private var clarificationAsked: Set<String> = []

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
        self.dayZeroClosed = repository.dayZeroClosed()
        if let loaded = try repository.loadSnapshot() {
            // Bike/drift backfill disabled for dogfood alongside the founding seed below — 2026-08-25.
            // let migrated = try SeedFactory.ensureFounding(in: loaded, now: now())
            // Q34 top-up stays on: a practice that promised seven checks today
            // needs its seven cases before the lid is drawn, and a new day is
            // the only thing that ever makes one missing.
            let migrated = SeedFactory.ensureOccurrences(in: loaded, now: now())
            snapshot = migrated
            if migrated != loaded {
                try repository.saveSnapshot(migrated)
            }
        } else {
            // Demo founding seed (push-ups / vegetables / bike) disabled for dogfood — 2026-08-25.
            // Re-enable (or restyle as onboarding examples) via SeedFactory.buildSeed(now:).
            // snapshot = try SeedFactory.buildSeed(now: now())
            snapshot = DeskSnapshot(subjects: [], cues: [], instances: [], widgets: [])
            try repository.saveSnapshot(snapshot)
        }
        let day = Calendar.current.startOfDay(for: now())
        surfacedDay = day
        surfacedPlaces = repository.surfacedPlaces(on: day)
        clarificationAsked = repository.clarificationAskedSubjects()
        undoableTurn = repository.loadUndo()
        closeDayZeroIfNeeded()
    }

    /// Q34: top up today's cases for a practice that promised several.
    ///
    /// Called where the desk arrives or changes shape — at load, after a talk
    /// turn, and when the lid comes back to the front on a new day. It is
    /// arithmetic and idempotent: with nothing missing it writes nothing, so
    /// calling it twice costs a comparison.
    func ensureOccurrences() {
        commit(reminders: true) { next in
            next = SeedFactory.ensureOccurrences(in: next, now: now())
        }
    }

    /// The day-0 chips above the composer. Only on a desk that has never held a
    /// subject — an empty Сегодня on a desk full of practices is a rest day.
    var showsDayZeroChips: Bool {
        DayZeroLaw.showsChips(subjects: snapshot.subjects, closed: dayZeroClosed)
    }

    var lid: LidProjection {
        LidProjectionLaw.project(
            now: now(),
            subjects: snapshot.subjects,
            instances: snapshot.instances,
            widgets: snapshot.widgets
        )
    }

    func subject(id: String) -> Subject? {
        snapshot.subjects.first { $0.id == id }
    }

    func showsOnLid(subjectId: String) -> Bool {
        subject(id: subjectId)?.status != .retired
    }

    /// The right to speak already lives in the law: `LidProjectionLaw` only
    /// emits a card the ladder is allowed to show. This stays as the one place
    /// the lid asks, so the projection is never second-guessed on screen.
    func surfaces(_ card: DriftCard) -> Bool {
        guard let subject = subject(id: card.subjectId) else { return false }
        return card.offer != .stop && DriftLaw.canAskNow(subject, now: now())
    }

    func cueFor(subjectId: String) -> Cue? {
        CueLaw.doTimeCue(in: snapshot.cues, subjectId: subjectId)
    }

    func surfaceCue(for widget: Widget) -> Cue? {
        CueLaw.surfaceCue(in: snapshot.cues, subjectId: widget.subjectId, widgetType: widget.type)
    }

    /// What sits behind the `?` on this step. Never rendered inline: an
    /// explanation is looked up, a correction must be seen (04).
    func explanations(for widget: Widget) -> [Cue] {
        ClarificationLaw.onDemandCues(in: snapshot.cues, subjectId: widget.subjectId)
    }

    func hasExplanation(for widget: Widget) -> Bool {
        ClarificationLaw.hasExplanation(in: snapshot.cues, subjectId: widget.subjectId)
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

    /// The cases the carousel lists: occurrences, never the hour a reminder
    /// stands on (Q34). The queue of a day is what happened, not what rang.
    func occurrenceInstances(for subjectId: String) -> [Instance] {
        SlotLaw.occurrenceInstances(
            subjectId: subjectId,
            instances: snapshot.instances,
            widgets: snapshot.widgets
        )
    }

    /// Close **this** occurrence, whatever type it wears.
    ///
    /// One mark on a group tile closes its own case and nothing else: there is
    /// no pointer to advance, and a later check never closes an earlier miss.
    /// A tick toggles, because a tick has always toggled; the other runtimes
    /// have one way to be finished and this is it.
    func closeOccurrence(widgetId: String) {
        guard let widget = widget(id: widgetId) else { return }
        switch widget.type {
        case .tick: toggleTick(widgetId: widgetId)
        case .counter: completeCounter(widgetId: widgetId)
        case .checklist: completeChecklist(widgetId: widgetId)
        case .timer: completeTimer(widgetId: widgetId)
        case .stepper: completeStepper(widgetId: widgetId)
        case .reminder: completeReminder(widgetId: widgetId)
        }
    }

    /// Where the kebab carousel opens. It must be a slot the carousel actually
    /// lists, so a live reminder does not park the selection on an hour that is
    /// no longer in the queue (Q34).
    func preferredInstanceId(subjectId: String) -> String? {
        let listed = occurrenceInstances(for: subjectId)
        if let live = templateWidget(subjectId: subjectId),
           listed.contains(where: { $0.id == live.instanceId })
        {
            return live.instanceId
        }
        return listed.last?.id
    }

    // MARK: - The hours of a grouped practice (R18)

    /// Today's group, when its marks really do wear the window's hours — the
    /// only shape the carousel may edit. `nil` for every ordinary practice, and
    /// the carousel then behaves exactly as it did.
    func hourGroup(subjectId: String) -> OccurrenceHourLaw.HourGroup? {
        OccurrenceHourLaw.group(subjectId: subjectId, in: snapshot, now: now())
    }

    func hourSlot(subjectId: String, instanceId: String) -> OccurrenceHourLaw.HourSlot? {
        OccurrenceHourLaw.slot(instanceId: instanceId, subjectId: subjectId, in: snapshot, now: now())
    }

    /// `+` on a grouped practice, after the wheels named an hour. Alarms are
    /// recomputed because the window changed — `enqueue`, never a bypass.
    @discardableResult
    func addHour(subjectId: String, clock: ClockTime) -> String? {
        var result = OccurrenceHourLaw.HourEdit.refused
        commit(reminders: true) { next in
            result = OccurrenceHourLaw.addHour(clock, subjectId: subjectId, in: &next, now: now())
        }
        switch result {
        case .added(let id), .alreadyStanding(let id): return id
        default: return nil
        }
    }

    @discardableResult
    func moveHour(subjectId: String, instanceId: String, to clock: ClockTime) -> Bool {
        var result = OccurrenceHourLaw.HourEdit.refused
        commit(reminders: true) { next in
            result = OccurrenceHourLaw.moveHour(
                instanceId: instanceId,
                subjectId: subjectId,
                to: clock,
                in: &next,
                now: now()
            )
        }
        if case .moved = result { return true }
        return false
    }

    /// Drops the hour **and** its check. Returns the slot the carousel should
    /// stand on afterwards, or `nil` when nothing was dropped.
    @discardableResult
    func dropHour(subjectId: String, instanceId: String) -> String? {
        var result = OccurrenceHourLaw.HourEdit.refused
        commit(reminders: true) { next in
            result = OccurrenceHourLaw.dropHour(
                instanceId: instanceId,
                subjectId: subjectId,
                in: &next,
                now: now()
            )
        }
        if case .dropped(let next) = result { return next }
        return nil
    }

    @discardableResult
    func addInstance(subjectId: String) -> String? {
        guard subject(id: subjectId) != nil else { return nil }
        // A grouped practice is added to by naming an hour, not by cloning the
        // tile in front of you: `+` here stamped «сейчас» on the new check and
        // put two «11:42» in a row on the phone (R18). The hour is asked for by
        // the carousel and lands through `addHour`.
        guard hourGroup(subjectId: subjectId) == nil else { return nil }
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

    /// Widgets the kebab header can still quiet down: the ones this subject is
    /// asking with right now. A done tile stays dim on Today until midnight.
    func postponeTargets(subjectId: String) -> [Widget] {
        snapshot.widgets.filter { widget in
            widget.subjectId == subjectId
                && (widget.status == .ready || widget.status == .running)
                && (widget.section == .today || widget.section == .lifetime || widget.section == .soon)
        }
    }

    /// `postpone` from the shared law: the tile leaves Today for Отложили and
    /// the alarm goes quiet. `when` is kept — postpone is "not now", not a
    /// deletion and not a skip.
    @discardableResult
    func postpone(subjectId: String) -> Bool {
        let ids = Set(postponeTargets(subjectId: subjectId).map(\.id))
        guard !ids.isEmpty else { return false }
        commit(reminders: true) { next in
            for index in next.widgets.indices where ids.contains(next.widgets[index].id) {
                next.widgets[index].section = .postponed
                next.widgets[index].status = .snoozed
            }
        }
        return true
    }

    /// `archive_widget` + `retire_subject` by the law: the object leaves the
    /// lid and the practice stops asking. 04-domain-model — "nothing is deleted
    /// as punishment": instances and cues stay exactly where they are, so the
    /// reason survives and Deeds can still open this practice.
    @discardableResult
    func removeFromLid(subjectId: String) -> Bool {
        guard let subject = subject(id: subjectId), subject.status != .retired else { return false }
        commit(reminders: true) { next in
            for index in next.widgets.indices where next.widgets[index].subjectId == subjectId {
                guard next.widgets[index].status != .archived else { continue }
                next.widgets[index].status = .archived
                next.widgets[index].version += 1
            }
            if let index = next.subjects.firstIndex(where: { $0.id == subjectId }) {
                next.subjects[index] = SubjectLaw.retire(next.subjects[index])
            }
        }
        journal(.subjectRetired, subjectId: subjectId)
        return true
    }

    func markCueSurfaced(widgetId: String, place: String) {
        guard let widget = widget(id: widgetId),
              let cue = surfaceCue(for: widget),
              widget.status != .done
        else { return }
        countSurfaced(cue: cue, widget: widget, place: place)
    }

    /// Opening the `?` is the on-demand surface actually happening — the same
    /// hit a do-time cue scores by appearing at rep one. Once per
    /// widget + place + day, with the cue in the key so a step carrying two
    /// explanations counts both. No `done` guard: a tile appearing is passive,
    /// tapping `?` is the person asking.
    func markExplanationsSurfaced(widgetId: String) {
        guard let widget = widget(id: widgetId) else { return }
        for cue in explanations(for: widget) {
            countSurfaced(cue: cue, widget: widget, place: "help|\(cue.id)")
        }
    }

    private func countSurfaced(cue: Cue, widget: Widget, place: String) {
        let day = Calendar.current.startOfDay(for: now())
        if day != surfacedDay {
            surfacedDay = day
            surfacedPlaces = repository.surfacedPlaces(on: day)
        }
        let key = "\(widget.id)|\(place)"
        guard surfacedPlaces.insert(key).inserted else { return }
        commit { next in
            guard let index = next.cues.firstIndex(where: { $0.id == cue.id }) else { return }
            next.cues[index].hits.surfaced += 1
        }
        journal(
            .cueSurfaced,
            subjectId: widget.subjectId,
            widgetId: widget.id,
            instanceId: widget.instanceId,
            cueId: cue.id,
            payload: ["place": place]
        )
    }

    /// Q32, once per practice: the first case closed on something the mouth
    /// explained. The ask itself is calm and answerable in one tap; the answer
    /// goes back into the current thread as an ordinary reply.
    func markClarificationAsked(subjectId: String) {
        if clarificationAsk == subjectId { clarificationAsk = nil }
        guard clarificationAsked.insert(subjectId).inserted else { return }
        journal(.clarificationAsked, subjectId: subjectId)
    }

    private func noteCaseCompleted(subjectId: String) {
        guard clarificationAsk == nil,
              ClarificationLaw.asksAfterFirstCase(
                  subjectId: subjectId,
                  cues: snapshot.cues,
                  instances: snapshot.instances,
                  alreadyAsked: clarificationAsked.contains(subjectId)
              )
        else { return }
        clarificationAsk = subjectId
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
                next.instances[instanceIndex].when = GroupLaw.closingStamp(
                    widget,
                    standing: next.instances[instanceIndex].when,
                    now: stamp
                )
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        noteCaseCompleted(subjectId: widget.subjectId)
    }

    /// One line of a checklist, on the tile or on Use. A finger tick is a
    /// finger tick: it moves the instance into `running`, writes the journal,
    /// and never appends a chat snapshot (never-do #7).
    func toggleChecklistItem(widgetId: String, itemId: String) {
        guard let widget = widget(id: widgetId), widget.type == .checklist else { return }
        let next = ChecklistLaw.toggle(widget.payload, itemId: itemId)
        guard next != widget.payload else { return }
        let wasReady = widget.status == .ready
        let wasDone = widget.status == .done
        commit { snapshot in
            guard let index = snapshot.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            snapshot.widgets[index].payload = next
            if wasReady || wasDone {
                snapshot.widgets[index].status = .running
                if wasDone { snapshot.widgets[index].when = nil }
            }
            if let instanceIndex = snapshot.instances.firstIndex(where: { $0.id == widget.instanceId }),
               wasReady || wasDone
            {
                snapshot.instances[instanceIndex].status = .inProgress
            }
        }
        if wasReady {
            journal(.instanceStarted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        }
        let counted = ChecklistLaw.progress(of: next)
        journal(
            .checklistItemToggled,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: [
                "item": itemId,
                "done": String(counted.done),
                "total": String(counted.total)
            ]
        )
    }

    /// «Готово» on a checklist. Same shape as `completeCounter`: the law ticks
    /// every remaining line so the tile never shows «2 из 5» beside a closed
    /// instance, the cue scores its hit, and the case closes.
    func completeChecklist(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .checklist, widget.status != .done else { return }
        let stamp = now()
        let cue = cueFor(subjectId: widget.subjectId)
        let finished = ChecklistLaw.setDone(widget.payload, true)
        commit { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].payload = finished
            next.widgets[index].status = .done
            next.widgets[index].when = stamp
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[instanceIndex].status = .completed
                next.instances[instanceIndex].when = GroupLaw.closingStamp(
                    widget,
                    standing: next.instances[instanceIndex].when,
                    now: stamp
                )
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        noteCaseCompleted(subjectId: widget.subjectId)
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
                next.instances[instanceIndex].when = GroupLaw.closingStamp(
                    widget,
                    standing: next.instances[instanceIndex].when,
                    now: stamp
                )
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
            noteCaseCompleted(subjectId: widget.subjectId)
        }
    }

    /// Start or stop a timer's run. What is written is the moment the run
    /// began (or the seconds it banked) — never a ticking number, so a run
    /// survives a background, a relaunch, and a desk that came from the server.
    func toggleTimerRun(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .timer else { return }
        let stamp = now()
        let wasRunning = TimerLaw.isRunning(widget.payload)
        let next = wasRunning
            ? TimerLaw.pause(widget.payload, now: stamp)
            : TimerLaw.start(widget.payload, now: stamp)
        guard next != widget.payload else { return }
        let wasReady = widget.status == .ready
        let wasDone = widget.status == .done
        commit { snapshot in
            guard let index = snapshot.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            snapshot.widgets[index].payload = next
            if wasReady || wasDone {
                snapshot.widgets[index].status = .running
                if wasDone { snapshot.widgets[index].when = nil }
            }
            if let instanceIndex = snapshot.instances.firstIndex(where: { $0.id == widget.instanceId }),
               wasReady || wasDone
            {
                snapshot.instances[instanceIndex].status = .inProgress
            }
        }
        if wasReady {
            journal(.instanceStarted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        }
        journal(
            wasRunning ? .timerPaused : .timerStarted,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: ["elapsed": String(TimerLaw.elapsed(next, now: stamp))]
        )
    }

    /// Back to the full length. The length the person named is not touched,
    /// and a reset is not a finished sitting — the case stays open.
    func resetTimer(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .timer else { return }
        let stamp = now()
        let wasRunning = TimerLaw.isRunning(widget.payload)
        let next = TimerLaw.reset(widget.payload)
        guard next != widget.payload else { return }
        commit { snapshot in
            guard let index = snapshot.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            snapshot.widgets[index].payload = next
        }
        if wasRunning {
            journal(
                .timerPaused,
                subjectId: widget.subjectId,
                widgetId: widgetId,
                instanceId: widget.instanceId,
                payload: ["elapsed": "0"]
            )
        }
    }

    /// «Готово» on a timer. The run stops and its seconds are banked, so the
    /// tile cannot keep counting past a closed case; then the case closes the
    /// same way the counter's does.
    func completeTimer(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .timer, widget.status != .done else { return }
        let stamp = now()
        let cue = cueFor(subjectId: widget.subjectId)
        let stopped = TimerLaw.pause(widget.payload, now: stamp)
        commit { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].payload = stopped
            next.widgets[index].status = .done
            next.widgets[index].when = stamp
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[instanceIndex].status = .completed
                next.instances[instanceIndex].when = GroupLaw.closingStamp(
                    widget,
                    standing: next.instances[instanceIndex].when,
                    now: stamp
                )
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(
            .instanceCompleted,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: ["elapsed": String(TimerLaw.elapsed(stopped, now: stamp))]
        )
        noteCaseCompleted(subjectId: widget.subjectId)
    }

    /// One beat of a stepper, pressed at the bottom of Use — never on the
    /// tile (04). A finger move: the journal records it, the chat does not
    /// (never-do #7).
    func stepForward(widgetId: String) {
        moveStepper(widgetId: widgetId, by: StepperLaw.forward)
    }

    func stepBack(widgetId: String) {
        moveStepper(widgetId: widgetId, by: StepperLaw.back)
    }

    private func moveStepper(widgetId: String, by move: (WidgetPayload) -> WidgetPayload) {
        guard let widget = widget(id: widgetId), widget.type == .stepper else { return }
        let next = move(widget.payload)
        guard next != widget.payload else { return }
        let wasReady = widget.status == .ready
        let wasDone = widget.status == .done
        commit { snapshot in
            guard let index = snapshot.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            snapshot.widgets[index].payload = next
            if wasReady || wasDone {
                snapshot.widgets[index].status = .running
                if wasDone { snapshot.widgets[index].when = nil }
            }
            if let instanceIndex = snapshot.instances.firstIndex(where: { $0.id == widget.instanceId }),
               wasReady || wasDone
            {
                snapshot.instances[instanceIndex].status = .inProgress
            }
        }
        if wasReady {
            journal(.instanceStarted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        }
        journal(
            .stepperMoved,
            subjectId: widget.subjectId,
            widgetId: widgetId,
            instanceId: widget.instanceId,
            payload: [
                "step": String(StepperLaw.position(of: next) + 1),
                "total": String(StepperLaw.beats(of: next).count)
            ]
        )
    }

    /// «Готово» on a stepper: the sequence ends standing on its last beat, and
    /// the case closes the way the counter's does.
    func completeStepper(widgetId: String) {
        guard let widget = widget(id: widgetId), widget.type == .stepper, widget.status != .done else { return }
        let stamp = now()
        let cue = cueFor(subjectId: widget.subjectId)
        let finished = StepperLaw.finish(widget.payload)
        commit { next in
            guard let index = next.widgets.firstIndex(where: { $0.id == widgetId }) else { return }
            next.widgets[index].payload = finished
            next.widgets[index].status = .done
            next.widgets[index].when = stamp
            if let instanceIndex = next.instances.firstIndex(where: { $0.id == widget.instanceId }) {
                next.instances[instanceIndex].status = .completed
                next.instances[instanceIndex].when = GroupLaw.closingStamp(
                    widget,
                    standing: next.instances[instanceIndex].when,
                    now: stamp
                )
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        noteCaseCompleted(subjectId: widget.subjectId)
    }

    func editReminderLatestBy(widgetId: String, latestBy: ClockTime) {
        guard let widget = widget(id: widgetId),
              let window = windowFor(subjectId: widget.subjectId)
        else { return }
        editReminderHour(widgetId: widgetId, from: window.latestBy, to: latestBy)
    }

    /// The picker on Use moves **one** hour of the window — the one the chip was
    /// showing. A practice that named seven keeps the other six (Q34).
    func editReminderHour(widgetId: String, from old: ClockTime, to latestBy: ClockTime) {
        guard let widget = widget(id: widgetId), widget.type == .reminder else { return }
        guard let window = windowFor(subjectId: widget.subjectId) else { return }
        let clock = ReminderClock.clamp(latestBy, to: window)
        let day = Calendar.current.startOfDay(for: widget.reminderFireAt ?? now())
        commit(reminders: true) { next in
            guard let widgetIndex = next.widgets.firstIndex(where: { $0.id == widgetId }),
                  let subjectIndex = next.subjects.firstIndex(where: { $0.id == widget.subjectId }),
                  var nextWindow = next.subjects[subjectIndex].window
            else { return }
            nextWindow.replaceHour(old, with: clock)
            next.subjects[subjectIndex].window = nextWindow
            // The widget's own hour is the first of them, as it always was.
            let fireAt = ReminderClock.date(on: day, clock: nextWindow.latestBy)
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
                next.instances[instanceIndex].when = GroupLaw.closingStamp(
                    widget,
                    standing: next.instances[instanceIndex].when,
                    now: stamp
                )
            }
            if let cue, let cueIndex = next.cues.firstIndex(where: { $0.id == cue.id }) {
                next.cues[cueIndex].hits.applied += 1
            }
        }
        if let cue {
            journal(.cueApplied, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId, cueId: cue.id)
        }
        journal(.instanceCompleted, subjectId: widget.subjectId, widgetId: widgetId, instanceId: widget.instanceId)
        noteCaseCompleted(subjectId: widget.subjectId)
    }

    /// Taking the offer. The rung the law chose is the only one on the card,
    /// so this never has to decide what "down" means.
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

    /// «Not now». The card goes quiet for one cadence period and comes back a
    /// rung lower. Two refusals of the offer to retire and it never comes back
    /// at all — the practice stays in Deeds without a rhythm (Q28).
    func refuseDrift(subjectId: String) {
        guard let card = lid.driftCard, card.subjectId == subjectId, surfaces(card) else { return }
        let stamp = now()
        commit(reminders: false) { next in
            guard let index = next.subjects.firstIndex(where: { $0.id == subjectId }) else { return }
            next.subjects[index] = DriftLaw.refuse(next.subjects[index], offer: card.offer, now: stamp)
        }
        journal(
            .driftAnswered,
            subjectId: subjectId,
            payload: ["offer": card.offer.rawValue, "answer": "refused"]
        )
    }

    /// The same merge a talk turn goes through (`ProgressMergeLaw`), for a desk
    /// pulled from `/v1/desk` (В3.1/M3) instead of from the mouth. No cue
    /// journal — that's talk-specific.
    ///
    /// The record of truth has just spoken, so the one step back goes with it:
    /// a desk from before a turn is not a thing to push over a server desk.
    func applyServerDesk(_ desk: DeskSnapshot) {
        let previous = snapshot
        commit(reminders: true) { next in
            next = ProgressMergeLaw.merge(incoming: desk, keepingProgressOf: previous)
        }
        forgetUndo()
    }

    /// - Parameter turn: where this turn sits in the thread, when the caller
    ///   knows. A turn that really changed the desk leaves the one step back
    ///   here; a turn that only explained leaves nothing and does not disturb
    ///   the offer standing above it.
    func applyTalk(_ desk: DeskSnapshot, toolCalls: [TalkToolCall] = [], turn: TalkTurnRef? = nil) {
        let previous = snapshot
        let written = desk.cues.filter { incoming in
            previous.cues.first { $0.id == incoming.id } != incoming
        }
        let touchedIds = Self.widgetIdsTouchedByTalk(toolCalls)
        commit(reminders: true) { next in
            next = ProgressMergeLaw.merge(
                incoming: desk,
                keepingProgressOf: previous,
                skipping: touchedIds
            )
        }
        if let turn, snapshot != previous {
            remember(UndoableTurn(before: previous, threadId: turn.threadId, turnId: turn.turnId, at: now()))
        }
        // A turn that promised seven checks a day has to leave seven of them on
        // the desk, and it does not do that itself: the mouth wrote the rhythm,
        // the law counts the cases (Q34).
        ensureOccurrences()
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

    /// Is this the turn the thread may still offer to take back? Asked per
    /// turn, so only one card in the whole conversation carries the control.
    func undoOffered(threadId: String, turnId: String) -> Bool {
        undoableTurn?.threadId == threadId && undoableTurn?.turnId == turnId
    }

    /// The one step back, taken **by the person** — the mouth has no name for
    /// this and never will (06 AI: the assistant does not undo itself).
    ///
    /// Structure returns to the desk as it stood before that turn; everything a
    /// finger did since is carried back over it by the same law a talk turn and
    /// a server desk go through, so a count, a tick or a run made after the turn
    /// survives the rollback (Q20, 06 AI #2). Reminders are recomputed, because
    /// a window may have just moved back — `commit(reminders: true)`, as
    /// everywhere.
    ///
    /// Nothing is deleted as punishment: the line, the answer and the snapshot
    /// stay in the thread and are marked undone by `TalkStore`. The offer is
    /// spent the moment it is taken — undoing an undo is a time machine.
    @discardableResult
    func undoLastTalk() -> UndoableTurn? {
        guard let record = undoableTurn else { return nil }
        let live = snapshot
        commit(reminders: true) { next in
            next = ProgressMergeLaw.merge(incoming: record.before, keepingProgressOf: live)
        }
        // The restored rhythm may promise several checks a day again, and the
        // cases behind them are counted by the law, not by the rollback (Q34).
        ensureOccurrences()
        forgetUndo()
        journal(
            .talkUndone,
            payload: ["thread": record.threadId, "turn": record.turnId]
        )
        return record
    }

    private func remember(_ record: UndoableTurn) {
        undoableTurn = record
        repository.saveUndo(record)
    }

    private func forgetUndo() {
        guard undoableTurn != nil else { return }
        undoableTurn = nil
        repository.clearUndo()
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
        InstanceLaw.preferredLive(in: snapshot.widgets, subjectId: subjectId, now: now())
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
            guard let index = next.subjects.firstIndex(where: { $0.id == subjectId }) else { return }
            // The body already wrote the commitment change (`moveToToday`,
            // `shrinkToOnceAWeek`, `retireSubject`). This only walks the
            // ladder: one more ask, stamped, so the next one waits a period.
            next.subjects[index].driftAsksMade += 1
            next.subjects[index].driftAskedAt = stamp
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

    private static func widgetIdsTouchedByTalk(_ toolCalls: [TalkToolCall]) -> Set<String> {
        Set(toolCalls.compactMap { call in
            guard call.ok else { return nil }
            switch call.name {
            case "update_widget", "create_widget":
                return call.arguments["widget_id"]?.string ?? call.arguments["id"]?.string
            default:
                return nil
            }
        })
    }

    private func commit(reminders: Bool = false, _ body: (inout DeskSnapshot) -> Void) {
        var next = snapshot
        body(&next)
        guard next != snapshot else { return }
        snapshot = next
        try? repository.saveSnapshot(next)
        closeDayZeroIfNeeded()
        if reminders {
            ReminderScheduler.enqueue(snapshot: next, now: now())
        }
    }

    private func closeDayZeroIfNeeded() {
        guard !dayZeroClosed, DayZeroLaw.closes(subjects: snapshot.subjects) else { return }
        repository.closeDayZero()
        dayZeroClosed = true
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
