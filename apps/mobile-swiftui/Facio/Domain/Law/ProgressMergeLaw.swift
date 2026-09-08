import Foundation

/// Structure comes from the incoming desk; **runtime progress stays local**.
///
/// One rule, three callers — a talk turn (`DeskStore.applyTalk`), a desk pulled
/// from the server (`DeskStore.applyServerDesk`), and the one-step undo of a
/// turn (`DeskStore.undoLastTalk`). Q20 says it plainly: structure is
/// last-write-wins, ticks and counts and elapsed runs are **not**, and a stale
/// structural write must never drop a set logged on this device (06, AI #2).
/// There is no second copy of this rule anywhere, and a fourth caller reuses it
/// rather than growing its own.
///
/// What counts as progress is exactly what a finger produced: the counter's
/// `count`, the tick's `done`, a checklist line's own `done`, the timer's
/// current run, the beat a stepper stands on — plus the closure those things
/// end in (the widget's `done` and its case). Everything else in the payload is
/// the *face* the mouth wrote (target, item text, seconds, beats, the hour) and
/// belongs to the incoming desk.
enum ProgressMergeLaw {
    /// - Parameters:
    ///   - incoming: the desk whose **structure** wins.
    ///   - local: the desk as this device has it right now.
    ///   - skipping: widget ids the incoming write named out loud. A tool call
    ///     that rewrote this very widget *is* the newest word about it, so its
    ///     state arrives whole (В1.4).
    static func merge(
        incoming: DeskSnapshot,
        keepingProgressOf local: DeskSnapshot,
        skipping: Set<String> = []
    ) -> DeskSnapshot {
        var next = incoming
        for widget in local.widgets {
            guard !skipping.contains(widget.id),
                  let index = next.widgets.firstIndex(where: { $0.id == widget.id }),
                  // A widget standing on another case is another case. Progress
                  // belongs to the instance it was made on, never to the fresh
                  // one a rebind put underneath.
                  next.widgets[index].instanceId == widget.instanceId,
                  // Archived and postponed are **structural** answers — «убрать»
                  // and «не сейчас». Carrying a count onto one of those would
                  // pull the tile back onto the lid the person just cleared.
                  next.widgets[index].status != .archived,
                  next.widgets[index].status != .snoozed
            else { continue }

            switch widget.status {
            case .running:
                next.widgets[index].payload = carry(progressOf: widget.payload, into: next.widgets[index].payload)
                next.widgets[index].status = .running
                carryCase(widget.instanceId, status: .inProgress, when: nil, into: &next)
            case .done where next.widgets[index].status != .done:
                next.widgets[index].payload = carry(progressOf: widget.payload, into: next.widgets[index].payload)
                next.widgets[index].status = .done
                next.widgets[index].when = widget.when
                carryCase(widget.instanceId, status: .completed, when: closingStamp(of: widget, in: local), into: &next)
            default:
                continue
            }
        }
        return next
    }

    // MARK: - Pieces

    private static func carry(progressOf local: WidgetPayload, into incoming: WidgetPayload) -> WidgetPayload {
        var merged = incoming
        if let count = local.count { merged.count = count }
        if let done = local.done { merged.done = done }
        if let startedAt = local.startedAt { merged.startedAt = startedAt }
        if let elapsed = local.elapsed { merged.elapsed = elapsed }
        // The list the mouth wrote is the list; only the ticks come from here,
        // matched line by line. A line the turn dropped drops its tick with it.
        if let mine = local.items, var lines = merged.items {
            for index in lines.indices {
                guard let tick = mine.first(where: { $0.id == lines[index].id }) else { continue }
                lines[index].done = tick.done
            }
            merged.items = lines
        }
        // The beat stands where the finger left it, but never past the end of a
        // sequence the turn just shortened.
        if let current = local.current {
            let ceiling = max(0, (merged.beats?.count ?? 0) - 1)
            merged.current = min(current, ceiling)
        }
        return merged
    }

    private static func carryCase(
        _ instanceId: String,
        status: InstanceStatus,
        when: Date?,
        into next: inout DeskSnapshot
    ) {
        guard let index = next.instances.firstIndex(where: { $0.id == instanceId }) else { return }
        guard next.instances[index].status != .completed else { return }
        next.instances[index].status = status
        if let when { next.instances[index].when = when }
    }

    /// A closed check keeps its own hour (`GroupLaw.closingStamp`), so a merge
    /// cannot restamp it to «now» and reshuffle a grouped day.
    private static func closingStamp(of widget: Widget, in local: DeskSnapshot) -> Date? {
        local.instances.first { $0.id == widget.instanceId }?.when
    }
}
