import Foundation

/// What a centered chat card draws.
///
/// A snapshot is **a picture of the moment it was written** (04, «Snapshot and
/// chapter»), so every number here comes off the card itself and none of it off
/// today's desk. That is the same discipline `InstanceFaceLaw` keeps one wire
/// further in — last week's slot must not be repainted with tonight's count —
/// and it reuses the same vocabulary, `InstanceFace`, so there is one idea of
/// what a widget's face is and not two.
///
/// The words, though, are ours. The service sends state; the sentence is built
/// here out of `DisplayCopy`, which means it is in the language the person is
/// reading rather than the language the service happens to be written in.
enum SnapshotFaceLaw {
    /// The picture, in the shape the carousel already knows.
    /// `paused` and a skipped reminder are states of the whole card, not faces,
    /// so they come back `blank` here and are handled by `line`.
    static func face(_ wire: SnapshotFace) -> InstanceFace {
        switch wire {
        case .counter(let count, let goal):
            .counter(count: count, goal: goal)
        case .tick(let done):
            .tick(done: done)
        case .checklist(let done, let total):
            .checklist(done: done, total: total)
        case .timer(let seconds):
            .timer(face: TimerLaw.face(seconds))
        case .stepper(let step, let total):
            .stepper(step: step, total: total)
        case .reminder(let clock, _, let skipped):
            skipped ? .blank : clock.map { InstanceFace.reminder(hour: $0) } ?? .blank
        case .paused, .blank:
            .blank
        }
    }

    /// The one line under the title.
    ///
    /// With no `face` the card came from a service built before R14 and carries
    /// only its own finished sentence: draw that, because a blank card is worse
    /// than a card in the wrong language.
    static func line(_ snapshot: ChatSnapshot) -> String {
        guard let wire = snapshot.face else { return snapshot.line }
        if case .paused = wire { return DisplayCopy.pausedNow }
        if case .reminder(_, _, let skipped) = wire, skipped { return DisplayCopy.reminderSkipped }
        return join(base: base(wire), detail: detail(wire, cue: snapshot.detail))
    }

    private static func base(_ wire: SnapshotFace) -> String? {
        switch face(wire) {
        case .counter(let count, let goal):
            DisplayCopy.counterFace(count: count, goal: goal)
        case .checklist(let done, let total):
            DisplayCopy.counterFace(count: done, goal: total)
        case .stepper(let step, let total):
            DisplayCopy.counterFace(count: step, goal: total)
        case .tick(let done):
            DisplayCopy.tickState(done: done)
        case .reminder(let hour):
            hour.shortLabel
        case .timer(let face):
            face
        case .blank:
            nil
        }
    }

    /// The door first, then the person's cue — the same order the card has
    /// always had. «The gym shuts at 22» is our sentence, so it is rebuilt from
    /// the clock; the cue is the person's own words and travels as it was said.
    private static func detail(_ wire: SnapshotFace, cue: String?) -> String? {
        if case .reminder(_, let closesAt, _) = wire, let closesAt {
            return DisplayCopy.doorPhrase(closesAt)
        }
        let trimmed = cue?.trimmingCharacters(in: .whitespacesAndNewlines)
        return (trimmed?.isEmpty ?? true) ? nil : trimmed
    }

    private static func join(base: String?, detail: String?) -> String {
        [base, detail].compactMap { $0 }.joined(separator: " · ")
    }
}
