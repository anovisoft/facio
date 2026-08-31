import Foundation

enum KebabLaw {
    /// `Open` on the inspector leads to **Inspect**, never to Use.
    /// Use is "do it now" and cannot swipe between instances; Inspect browses
    /// them (03-product, never-do #17).
    static func openRoute(subjectId: String, instanceId: String) -> DeskRoute {
        .inspect(subjectId: subjectId, instanceId: instanceId)
    }

    /// `z` is a *prepared future* instance. Only when there is none does the
    /// carousel show `+` — the bike case from 03-product.
    static func showsAddSlot(instances: [Instance], now: Date) -> Bool {
        !instances.contains { preparedFuture($0, now: now) }
    }

    /// The `z` slot: prepared and on a later day than today. Today's prepared
    /// instance is the one in the middle, not the future one.
    static func preparedFuture(_ instance: Instance, now: Date) -> Bool {
        guard instance.status == .prepared else { return false }
        return instance.when > now && !Calendar.current.isDate(instance.when, inSameDayAs: now)
    }
}
