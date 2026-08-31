import Foundation

/// The timer runtime, ported 1:1 from `facio_domain.runtime`.
/// Elapsed seconds are arithmetic over `startedAt` and the clock — nothing
/// ticks in storage, so a run survives a relaunch, a background, and a desk
/// that came back from the server.
enum TimerLaw {
    static func isRunning(_ payload: WidgetPayload) -> Bool {
        payload.startedAt != nil
    }

    /// Banked seconds plus the run that is going. A `startedAt` in the future
    /// — a clock that moved back — reads as a run with nothing in it yet, not
    /// as a debt.
    static func elapsed(_ payload: WidgetPayload, now: Date) -> Int {
        let banked = max(0, payload.elapsed ?? 0)
        guard let started = payload.startedAt else { return banked }
        return banked + max(0, Int(now.timeIntervalSince(started)))
    }

    static func remaining(_ payload: WidgetPayload, now: Date) -> Int {
        max(0, max(0, payload.seconds ?? 0) - elapsed(payload, now: now))
    }

    /// The named length is spent. A timer with no length never gets there.
    static func isDone(_ payload: WidgetPayload, now: Date) -> Bool {
        let total = payload.seconds ?? 0
        return total > 0 && elapsed(payload, now: now) >= total
    }

    /// Begin, or resume. Starting a running timer is a no-op — a second tap on
    /// start must not move `startedAt` and throw away the minutes.
    static func start(_ payload: WidgetPayload, now: Date) -> WidgetPayload {
        guard !isRunning(payload) else { return payload }
        var next = payload
        next.startedAt = now
        next.elapsed = max(0, payload.elapsed ?? 0)
        return next
    }

    /// Stop the run and bank what it produced.
    static func pause(_ payload: WidgetPayload, now: Date) -> WidgetPayload {
        guard isRunning(payload) else { return payload }
        var next = payload
        next.elapsed = elapsed(payload, now: now)
        next.startedAt = nil
        return next
    }

    /// Back to the full length. The length itself is not touched.
    static func reset(_ payload: WidgetPayload) -> WidgetPayload {
        var next = payload
        next.startedAt = nil
        next.elapsed = 0
        return next
    }

    /// `m:ss` — the face of a timer, in no language at all.
    static func face(_ seconds: Int) -> String {
        let safe = max(0, seconds)
        return String(format: "%d:%02d", safe / 60, safe % 60)
    }
}
