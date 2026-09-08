import Foundation

/// Adding, moving and dropping the hours of a grouped practice **by hand**.
///
/// Q34 put the hours in the subject's **window** and the checks in the law;
/// R16 laid one onto the other and drew them as a single tile; R17 then hid
/// the reminder tile whenever the group already says every hour. That last
/// step is why this exists: with the reminder gone from the lid, the carousel
/// is the only place left where a person can correct an hour, and `+` was
/// stamping «сейчас» onto a new check without asking.
///
/// Three rules hold the whole thing together.
///
/// * **The hour lives in the window.** A case carries the hour it is *for*
///   (`Instance.when`), and that is a copy `SeedFactory.ensureOccurrences`
///   re-lays from the window every time — never a second source of truth.
/// * **Hours and checks stay equal in number.** R16 lays hours onto cases only
///   when the window names exactly as many as there are; break that and the
///   group silently loses its hours and R17 hands the reminder tile back. So a
///   new hour arrives with a new case *and* a raised count, and a dropped one
///   takes all three away together.
/// * **A closed check is history.** It is not moved and it is not dropped.
///
/// The model does not take part: this is a finger on a wheel, and the law
/// counts. Nothing here invents an hour nobody said.
enum OccurrenceHourLaw {
    /// The group of today, when its marks really do wear the window's hours.
    ///
    /// Deliberately the same test R17 hides the reminder tile by, not the
    /// looser «this subject has a group»: with three hours against seven checks
    /// the hours were never laid onto the cases, so there is no hour on a slot
    /// to edit, and the reminder tile is still on the lid saying them.
    struct HourGroup: Equatable {
        var groupId: String
        var window: TimeWindow
        var marks: [GroupMark]

        var total: Int { marks.count }
    }

    /// One slot of that group, and what may be done to it.
    struct HourSlot: Equatable {
        var instanceId: String
        var widgetId: String
        var hour: ClockTime
        /// Closed: `completed` — already history (contract 4).
        var closed: Bool

        var canMove: Bool { !closed }
        /// The last hour cannot go: a window with no hour cannot fire and
        /// cannot be drawn (`hours_required` in the law refuses it too).
        var canDrop: Bool
    }

    enum HourEdit: Equatable {
        case added(instanceId: String)
        /// The window is idempotent, so naming an hour it already holds changes
        /// nothing at all — and must not add a second check onto that minute.
        case alreadyStanding(instanceId: String)
        case moved(instanceId: String)
        case dropped(nextSelection: String?)
        case refused
    }

    static func group(subjectId: String, in snapshot: DeskSnapshot, now: Date) -> HourGroup? {
        guard let subject = snapshot.subjects.first(where: { $0.id == subjectId }),
              subject.status != .retired,
              let window = subject.window
        else { return nil }
        let groupId = GroupLaw.key(subjectId: subjectId, day: now)
        guard let face = GroupLaw.face(
            of: groupId,
            widgets: snapshot.widgets,
            instances: snapshot.instances,
            now: now
        ),
            face.total > 1,
            window.hours.count == face.total,
            GroupLaw.saysEveryHour(face, window: window)
        else { return nil }
        return HourGroup(groupId: groupId, window: window, marks: face.marks)
    }

    static func slot(
        instanceId: String,
        subjectId: String,
        in snapshot: DeskSnapshot,
        now: Date
    ) -> HourSlot? {
        guard let group = group(subjectId: subjectId, in: snapshot, now: now),
              let mark = group.marks.first(where: { $0.instanceId == instanceId }),
              let hour = mark.hour
        else { return nil }
        let completed = snapshot.instances.first { $0.id == instanceId }?.status == .completed
        let closed = mark.done || completed
        return HourSlot(
            instanceId: instanceId,
            widgetId: mark.widgetId,
            hour: hour,
            closed: closed,
            canDrop: !closed && group.window.hours.count > 1
        )
    }

    // MARK: - The three edits

    /// `+` asked for an hour and got one. The hour goes into the window, the
    /// check appears beside it, and the promise counts one more.
    static func addHour(
        _ clock: ClockTime,
        subjectId: String,
        in snapshot: inout DeskSnapshot,
        now: Date
    ) -> HourEdit {
        guard let group = group(subjectId: subjectId, in: snapshot, now: now) else { return .refused }
        if let standing = group.marks.first(where: { $0.hour == clock }) {
            return .alreadyStanding(instanceId: standing.instanceId)
        }
        guard let subjectIndex = snapshot.subjects.firstIndex(where: { $0.id == subjectId }),
              let template = snapshot.widgets.first(where: { $0.id == group.marks[0].widgetId })
        else { return .refused }

        var window = group.window
        window.addHour(clock)
        guard let cadence = try? Cadence.of(count: window.hours.count, period: .day) else { return .refused }
        snapshot.subjects[subjectIndex].window = window
        // The promise and the hours move together (Q34): N stated hours are N
        // checks. Leave the count alone and tomorrow's top-up writes N cases
        // for N+1 hours, R16 stops laying them, and the group goes anonymous.
        snapshot.subjects[subjectIndex].cadence = cadence

        let at = ReminderClock.date(on: now, clock: clock)
        let instanceId = "\(subjectId)-\(UUID().uuidString)"
        snapshot.instances.append(
            Instance(id: instanceId, subjectId: subjectId, when: at, status: .prepared)
        )
        snapshot.subjects[subjectIndex].instanceIds.append(instanceId)
        var widget = InstanceLaw.newWidget(
            from: template,
            instanceId: instanceId,
            payload: InstanceLaw.resetPayload(of: template, now: at, window: window),
            now: at
        )
        widget.when = at
        widget.groupId = group.groupId
        snapshot.widgets.append(widget)

        snapshot = settle(snapshot, now: now)
        return .added(instanceId: instanceId)
    }

    /// The slot's own hour changes. The window moves it, the case rides along.
    static func moveHour(
        instanceId: String,
        subjectId: String,
        to clock: ClockTime,
        in snapshot: inout DeskSnapshot,
        now: Date
    ) -> HourEdit {
        guard let group = group(subjectId: subjectId, in: snapshot, now: now),
              let slot = slot(instanceId: instanceId, subjectId: subjectId, in: snapshot, now: now),
              slot.canMove,
              let subjectIndex = snapshot.subjects.firstIndex(where: { $0.id == subjectId })
        else { return .refused }
        if clock == slot.hour { return .moved(instanceId: instanceId) }
        // Two checks on one minute is one check with a duplicate: the window
        // would fold them and the two numbers would come apart.
        guard !group.window.hours.contains(clock) else { return .refused }

        var window = group.window
        window.replaceHour(slot.hour, with: clock)
        snapshot.subjects[subjectIndex].window = window

        let at = ReminderClock.date(on: now, clock: clock)
        if let index = snapshot.instances.firstIndex(where: { $0.id == instanceId }) {
            snapshot.instances[index].when = at
        }
        if let index = snapshot.widgets.firstIndex(where: { $0.id == slot.widgetId }) {
            snapshot.widgets[index].when = at
        }
        snapshot = settle(snapshot, now: now)
        return .moved(instanceId: instanceId)
    }

    /// The hour leaves the window and the check leaves with it. Not a deletion
    /// as punishment (04) — the person is taking back an hour they named.
    static func dropHour(
        instanceId: String,
        subjectId: String,
        in snapshot: inout DeskSnapshot,
        now: Date
    ) -> HourEdit {
        guard let group = group(subjectId: subjectId, in: snapshot, now: now),
              let slot = slot(instanceId: instanceId, subjectId: subjectId, in: snapshot, now: now),
              slot.canDrop,
              let subjectIndex = snapshot.subjects.firstIndex(where: { $0.id == subjectId })
        else { return .refused }

        var window = group.window
        guard window.removeHour(slot.hour) else { return .refused }
        guard let cadence = try? Cadence.of(count: window.hours.count, period: .day) else { return .refused }
        snapshot.subjects[subjectIndex].window = window
        snapshot.subjects[subjectIndex].cadence = cadence
        snapshot.subjects[subjectIndex].instanceIds.removeAll { $0 == instanceId }
        snapshot.instances.removeAll { $0.id == instanceId }
        snapshot.widgets.removeAll { $0.id == slot.widgetId }

        // Down to one check a day is not a group any more. Clearing the stamp
        // keeps a stale `group_id` from following the practice around; `cells`
        // would draw it as a single tile anyway, but a dead id on the desk is
        // exactly the field R16 found lying around unused.
        if window.hours.count < 2 {
            for index in snapshot.widgets.indices where snapshot.widgets[index].groupId == group.groupId {
                snapshot.widgets[index].groupId = nil
            }
        }

        snapshot = settle(snapshot, now: now)
        let left = group.marks.filter { $0.instanceId != instanceId }
        return .dropped(nextSelection: left.last?.instanceId)
    }

    /// How many checks this practice holds today, counted the way R16 counts
    /// them — the alarm's own case is an hour, not a check.
    static func occurrenceCount(subjectId: String, in snapshot: DeskSnapshot, on day: Date) -> Int {
        let hours = SlotLaw.hourInstanceIds(subjectId: subjectId, widgets: snapshot.widgets)
        return snapshot.instances.filter {
            $0.subjectId == subjectId
                && SlotLaw.isSameDay($0.when, day)
                && !hours.contains($0.id)
        }.count
    }

    /// One place decides which case wears which hour, and it is R16's top-up.
    /// Running it after every edit is why an edit cannot invent an ordering of
    /// its own — and it is idempotent, so it costs a comparison when nothing
    /// is out of place.
    private static func settle(_ snapshot: DeskSnapshot, now: Date) -> DeskSnapshot {
        SeedFactory.ensureOccurrences(in: snapshot, now: now)
    }
}
