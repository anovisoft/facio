import Foundation

/// What one carousel slot draws.
///
/// 03-product, «Carousel = instances, not schema versions»: the slots of one
/// subject are `[v1][v1][v2]…[YYY][z]` — **the face of that session**, not a
/// diff of tonight. So the face is read off the widget bound to *that*
/// instance, with that instance's payload and that widget's `version`, and
/// never off today's live widget: last week's set must not be repainted with
/// tonight's number.
///
/// It is a picture, not a runtime (never-do #6). The timer face is a number
/// frozen at the moment the slot was drawn, the stepper says where it stood,
/// the checklist says how much of it was ticked — nothing here ticks, counts
/// down or can be pressed.
enum InstanceFace: Equatable {
    case counter(count: Int, goal: Int?)
    case tick(done: Bool)
    case checklist(done: Int, total: Int)
    case reminder(hour: ClockTime)
    case timer(face: String)
    case stepper(step: Int, total: Int)
    /// Nothing to draw yet: the prepared future case `z`, or a day whose widget
    /// was rebound onto a later instance and left no face behind.
    case blank
}

enum InstanceFaceLaw {
    /// `widget` is the one bound to this very instance
    /// (`DeskStore.widget(instanceId:)`), or `nil` when a standing widget was
    /// rebound forward and this day kept no object of its own.
    static func face(instance: Instance, widget: Widget?, now: Date) -> InstanceFace {
        // `z` stays exactly as it was: a prepared future case has no face yet,
        // only a date and «готовится».
        if KebabLaw.preparedFuture(instance, now: now) { return .blank }
        guard let widget, widget.instanceId == instance.id else { return .blank }
        switch widget.type {
        case .counter:
            return .counter(count: widget.counterCount, goal: widget.counterGoal)
        case .tick:
            return .tick(done: widget.isTickDone)
        case .checklist:
            let progress = ChecklistLaw.progress(of: widget.payload)
            guard progress.total > 0 else { return .blank }
            return .checklist(done: progress.done, total: progress.total)
        case .reminder:
            guard let fireAt = widget.reminderFireAt else { return .blank }
            let parts = Calendar.current.dateComponents([.hour, .minute], from: fireAt)
            return .reminder(hour: ClockTime(hour: parts.hour ?? 0, minute: parts.minute ?? 0))
        case .timer:
            // Frozen at the single moment the carousel was drawn. A running
            // timer belongs on the lid and on Use, never in a slot.
            let seconds = TimerLaw.remaining(widget.payload, now: now)
            guard (widget.payload.seconds ?? 0) > 0 else { return .blank }
            return .timer(face: TimerLaw.face(seconds))
        case .stepper:
            let beats = StepperLaw.beats(of: widget.payload)
            guard !beats.isEmpty else { return .blank }
            return .stepper(step: StepperLaw.position(of: widget.payload) + 1, total: beats.count)
        }
    }
}
