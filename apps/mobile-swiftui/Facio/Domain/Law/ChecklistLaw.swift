import Foundation

/// The checklist runtime, ported 1:1 from `facio_domain.runtime`.
/// Pure functions over a payload: progress is counted, never stored, and a
/// tick that addresses a line nobody has cannot invent one.
enum ChecklistLaw {
    static func items(of payload: WidgetPayload) -> [ChecklistItem] {
        payload.items ?? []
    }

    /// `(done, total)`. Derived the way drift is derived — no saved number to
    /// fall out of step with the ticks.
    static func progress(of payload: WidgetPayload) -> (done: Int, total: Int) {
        let rows = items(of: payload)
        return (rows.filter(\.done).count, rows.count)
    }

    /// Every line ticked. An empty list is not done — there was nothing to do.
    static func isDone(_ payload: WidgetPayload) -> Bool {
        let counted = progress(of: payload)
        return counted.total > 0 && counted.done == counted.total
    }

    static func toggle(_ payload: WidgetPayload, itemId: String) -> WidgetPayload {
        let rows = items(of: payload)
        guard rows.contains(where: { $0.id == itemId }) else { return payload }
        var next = payload
        next.items = rows.map { row in
            guard row.id == itemId else { return row }
            var flipped = row
            flipped.done.toggle()
            return flipped
        }
        return next
    }

    /// Tick or untick the whole list — what «Готово» on Use means.
    static func setDone(_ payload: WidgetPayload, _ done: Bool) -> WidgetPayload {
        let rows = items(of: payload)
        guard !rows.isEmpty else { return payload }
        var next = payload
        next.items = rows.map { row in
            var copy = row
            copy.done = done
            return copy
        }
        return next
    }
}
