import Foundation

/// The client half of «Ask about a phrase, keep the answer» (05).
///
/// The service decides what becomes a cue; this decides what the client is
/// allowed to claim about a selection, where an explanation is allowed to
/// appear, and when the one clarity check is due. All of it is arithmetic over
/// the desk — no model, and no second copy of the cue defaults (`CueLaw`).
enum ClarificationLaw {
    /// What a selected phrase hangs on, as far as the client knows: the widget
    /// the talk sheet stands over and the subject behind it. Never a guess —
    /// an unbound selection travels bare and comes back as text only, because
    /// a subject invented here is exactly the orphan cue 04 forbids.
    static func selection(
        quote: String,
        focusedWidgetId: String?,
        widgets: [Widget]
    ) -> TalkSelection? {
        let phrase = quote.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !phrase.isEmpty else { return nil }
        let widget = focusedWidgetId.flatMap { id in widgets.first { $0.id == id } }
        return TalkSelection(
            quote: phrase,
            widgetId: widget?.id,
            subjectId: widget?.subjectId,
            stepId: nil
        )
    }

    /// Explanations, in the order they were written. They live behind the `?`
    /// on the step and nowhere else: `clarification` inline at do-time turns rep
    /// one into a wall of text and P9 dies by drowning (04, never-do #24 table).
    static func onDemandCues(in cues: [Cue], subjectId: String) -> [Cue] {
        cues.filter { $0.subjectId == subjectId && $0.surface == .onDemand }
    }

    static func hasExplanation(in cues: [Cue], subjectId: String) -> Bool {
        !onDemandCues(in: cues, subjectId: subjectId).isEmpty
    }

    /// Q32: a method delivered is not a method understood. After the **first**
    /// completed case of a practice the mouth wrote a cue for, ask once whether
    /// the explanation landed. Never twice, never on every case — the ask is a
    /// check, and a check that repeats is nagging (P8).
    static func asksAfterFirstCase(
        subjectId: String,
        cues: [Cue],
        instances: [Instance],
        alreadyAsked: Bool
    ) -> Bool {
        guard !alreadyAsked else { return false }
        guard cues.contains(where: { $0.subjectId == subjectId && $0.origin != nil }) else { return false }
        let completed = instances.filter { $0.subjectId == subjectId && $0.status == .completed }
        return completed.count == 1
    }
}
