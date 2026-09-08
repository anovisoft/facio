import SwiftUI

struct InspectScreen: View {
    let subjectId: String
    let instanceId: String

    @Environment(DeskStore.self) private var store
    @State private var selectedId: String
    /// Inspect's `+` is the same `+` (R18): a practice that states hours is
    /// asked which one, through the same wheels Use opens.
    @State private var hourEdit: ReminderTimeEdit?

    init(subjectId: String, instanceId: String) {
        self.subjectId = subjectId
        self.instanceId = instanceId
        _selectedId = State(initialValue: instanceId)
    }

    var body: some View {
        // The day strip lists occurrences, never the hour a reminder stands on
        // (Q34) — the same law the kebab carousel already reads, not a second
        // filter written next to it. A practice whose only case is its alarm
        // keeps it, because the bike's alarm is its ride (R11).
        let instances = store.occurrenceInstances(for: subjectId)
        let selected = Self.selection(in: instances, preferring: selectedId, arrivedOn: instanceId)
        let origin = SlotLaw.startOfDay(for: Date())
        let horizon = SlotLaw.horizon(desk: store.snapshot, origin: origin)
        let laterHere = horizon.later.filter { day in
            store.snapshot.instances.contains { instance in
                instance.subjectId == subjectId && SlotLaw.isSameDay(instance.when, day)
            }
        }
        VStack(alignment: .leading, spacing: 20) {
            if let selected {
                Text(DisplayCopy.loudDate(selected.when))
                    .font(.largeTitle.weight(.bold))
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
                if store.subject(id: subjectId)?.status == .paused {
                    Text(DisplayCopy.pausedNow)
                        .font(.title3)
                        .foregroundStyle(.secondary)
                } else {
                    Text(DisplayCopy.instanceStatus(selected.status))
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
            }
            InspectHorizonStrip(
                days: horizon.days,
                subjectId: subjectId,
                selectedId: selectedId,
                onSelectInstance: { selectedId = $0 }
            )
            ForEach(laterHere, id: \.timeIntervalSinceReferenceDate) { day in
                Text(DisplayCopy.loudDate(day))
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.secondary)
            }
            InstanceStrip(instances: instances, selectedId: $selectedId, onAdd: add)
            if let selected {
                InspectBody(
                    instance: selected,
                    widget: store.widget(instanceId: selected.id),
                    cue: store.cueFor(subjectId: subjectId),
                    window: store.windowFor(subjectId: subjectId)
                )
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .navigationTitle(DisplayCopy.title(subjectId: subjectId, stored: store.subject(id: subjectId)?.title ?? subjectId))
        .toolbarTitleDisplayMode(.inline)
        .facioChrome()
        // Arriving on a case the strip does not list (a Soon reminder tile
        // hands over its hour) must not leave the page without a date: the
        // selection settles onto a case that is really in the queue, once,
        // rather than the screen going blank until something else changes.
        .onAppear {
            if let selected, selected.id != selectedId { selectedId = selected.id }
        }
        .onChange(of: instanceId) { _, id in
            selectedId = id
        }
        .onChange(of: instances.map(\.id)) { _, ids in
            if !ids.contains(selectedId) {
                selectedId = ids.last ?? instanceId
            }
        }
        .sheet(item: $hourEdit) { edit in
            ReminderTimePickerSheet(edit: edit) { clock in
                if let landed = store.addHour(subjectId: subjectId, clock: clock) {
                    selectedId = landed
                }
            }
        }
    }

    /// Which case the loud date and the body are about, once the queue is the
    /// filtered one.
    ///
    /// The chip the finger picked wins. The case Inspect was opened on is the
    /// fallback, and when even that is not in the queue — the reminder's hour,
    /// handed over by a glance tile — the last listed case stands in. Filtering
    /// removes a slot; it must not remove the selection.
    static func selection(in instances: [Instance], preferring selectedId: String, arrivedOn instanceId: String) -> Instance? {
        instances.first { $0.id == selectedId }
            ?? instances.first { $0.id == instanceId }
            ?? instances.last
    }

    private func add() {
        if let group = store.hourGroup(subjectId: subjectId) {
            hourEdit = ReminderTimeEdit(
                id: subjectId,
                window: group.window,
                start: ReminderClock.nextHour(window: group.window, now: Date())
            )
            return
        }
        if let created = store.addInstance(subjectId: subjectId) {
            selectedId = created
        }
    }
}

private struct InspectBody: View {
    let instance: Instance
    let widget: Widget?
    let cue: Cue?
    let window: TimeWindow?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let widget {
                switch widget.type {
                case .counter:
                    Text(DisplayCopy.counterFace(count: widget.counterCount, goal: widget.counterGoal))
                        .font(.system(size: 44, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)
                    if let cue {
                        Text(cue.text)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(.primary)
                    }
                case .tick:
                    HStack(spacing: 12) {
                        Image(systemName: widget.isTickDone ? "checkmark.circle.fill" : "circle")
                            .font(.system(size: 44))
                            .foregroundStyle(widget.isTickDone ? .primary : .secondary)
                            .accessibilityHidden(true)
                        Text(DisplayCopy.tickState(done: widget.isTickDone))
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                case .reminder:
                    if let window {
                        Text(DisplayCopy.succeedBy(window))
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(.primary)
                    }
                    if let cue {
                        Text(cue.text)
                            .font(.body)
                            .foregroundStyle(.secondary)
                    }
                case .checklist, .timer, .stepper:
                    EmptyView()
                }
            }
        }
        .accessibilityElement(children: .combine)
    }
}
