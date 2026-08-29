import Foundation

/// The stepper runtime, ported 1:1 from `facio_domain.runtime`.
/// One number is the whole state, and it is clamped into the beats that
/// actually exist — a sequence rewritten shorter leaves the person on the last
/// beat, never crashes and never quietly sends them back to the start.
enum StepperLaw {
    static func beats(of payload: WidgetPayload) -> [String] {
        payload.beats ?? []
    }

    static func position(of payload: WidgetPayload) -> Int {
        let rows = beats(of: payload)
        guard !rows.isEmpty else { return 0 }
        return min(max(payload.current ?? 0, 0), rows.count - 1)
    }

    static func beat(of payload: WidgetPayload) -> String? {
        let rows = beats(of: payload)
        guard !rows.isEmpty else { return nil }
        return rows[position(of: payload)]
    }

    static func isLast(_ payload: WidgetPayload) -> Bool {
        let rows = beats(of: payload)
        return !rows.isEmpty && position(of: payload) == rows.count - 1
    }

    static func isFirst(_ payload: WidgetPayload) -> Bool {
        !beats(of: payload).isEmpty && position(of: payload) == 0
    }

    /// One beat on. The last beat does not roll over into the first — a
    /// sequence that wraps is a carousel, and this is a thing being done once.
    static func forward(_ payload: WidgetPayload) -> WidgetPayload {
        let rows = beats(of: payload)
        guard !rows.isEmpty else { return payload }
        var next = payload
        next.current = min(position(of: payload) + 1, rows.count - 1)
        return next
    }

    /// One beat back. The first beat does not wrap to the end.
    static func back(_ payload: WidgetPayload) -> WidgetPayload {
        let rows = beats(of: payload)
        guard !rows.isEmpty else { return payload }
        var next = payload
        next.current = max(0, position(of: payload) - 1)
        return next
    }

    /// Finished means standing on the last beat, not reset to the first: next
    /// time is a new instance, and that one starts at zero.
    static func finish(_ payload: WidgetPayload) -> WidgetPayload {
        let rows = beats(of: payload)
        guard !rows.isEmpty else { return payload }
        var next = payload
        next.current = rows.count - 1
        return next
    }
}
