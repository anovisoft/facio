import Foundation

/// One tile for the occurrences of one subject inside one period (Q34).
///
/// Mirror of `facio_domain/groups.py`. The count stays in the law — seven
/// checks are seven cases and seven widgets, each closed on its own — and only
/// the drawing changes: the lid draws the group **once**, through `group_id`,
/// the field 04 declared from the start and nothing had ever used.
///
/// The face borrows the stepper's compactness (the next hour large, `3/7`, a
/// row of marks) and refuses its **pointer**. There is no "current beat" here:
/// marks are independent and unordered, because a pointer cannot record «did 10
/// and 15, missed 12», and the miss is the product.
enum GroupLaw {
    static let separator = ":"

    /// The id every occurrence of one subject on one day carries. Derived, not
    /// invented: topping the same day up twice re-stamps and never splits.
    static func key(subjectId: String, day: Date) -> String {
        "\(subjectId)\(separator)\(SlotLaw.dayKey(day))"
    }

    /// Whether this occurrence is struck off. `skipped` is not `done`: a check
    /// that did not happen must not be drawn closed.
    static func isClosed(_ widget: Widget) -> Bool {
        if widget.status == .done { return true }
        if widget.type == .tick, widget.payload.done == true { return true }
        return false
    }

    static func members(of groupId: String, in widgets: [Widget]) -> [Widget] {
        widgets.filter { $0.groupId == groupId }
    }

    /// The moment to write on the **case** being closed.
    ///
    /// An occurrence inside a group keeps the hour it is for. That hour is the
    /// only thing telling the 15:00 check from the 12:00 one, so rewriting it
    /// to «now» the moment it is ticked would put the seven anonymous squares
    /// straight back — and would let the next top-up hand the hours out in a
    /// different order. A case outside a group is stamped with now, exactly as
    /// it always was.
    static func closingStamp(_ widget: Widget, standing: Date?, now: Date) -> Date {
        guard widget.groupId != nil, let standing else { return now }
        return standing
    }

    /// What one group tile draws, or `nil` when no widget carries that id.
    static func face(
        of groupId: String,
        widgets: [Widget],
        instances: [Instance],
        now: Date
    ) -> GroupFace? {
        let rows = members(of: groupId, in: widgets)
        guard let first = rows.first else { return nil }
        var whenOf: [String: Date] = [:]
        for instance in instances { whenOf[instance.id] = instance.when }
        let marks = rows
            .map { widget in
                GroupMark(
                    widgetId: widget.id,
                    instanceId: widget.instanceId,
                    hour: (whenOf[widget.instanceId] ?? widget.when).map(ReminderClock.clock(from:)),
                    done: isClosed(widget)
                )
            }
            .sorted { lhs, rhs in
                let left = lhs.hour ?? ClockTime(hour: 23, minute: 59, second: 59)
                let right = rhs.hour ?? ClockTime(hour: 23, minute: 59, second: 59)
                if left != right { return left < right }
                return lhs.widgetId < rhs.widgetId
            }
        return GroupFace(
            id: groupId,
            subjectId: first.subjectId,
            title: first.title,
            nextHour: nextHour(marks: marks, now: now),
            done: marks.filter(\.done).count,
            marks: marks
        )
    }

    /// The hour the tile shows large: the nearest one still ahead and still
    /// open. Past-and-missed is not promoted into the big number — the day
    /// already moved on — but it is not swept away either: its mark stays open
    /// in the row. With the whole day behind, the first hour still open is what
    /// is left to say; with nothing open the group is finished.
    static func nextHour(marks: [GroupMark], now: Date) -> ClockTime? {
        let clock = ReminderClock.clock(from: now)
        let open = marks.filter { !$0.done && $0.hour != nil }
        if let ahead = open.first(where: { ($0.hour ?? clock) >= clock }) { return ahead.hour }
        return open.first?.hour
    }

    /// Whether the group already names every hour this practice stands on.
    ///
    /// A reminder tile draws the subject's **window** — the nearest hour large
    /// and the rest of them small — so when the marks carry those same hours,
    /// the two tiles say one thing twice and the lid is a second inventory
    /// (P10). The test is not «is there a group» but «does the group already
    /// say it».
    ///
    /// The distinction is not academic. Hours land on occurrences only when the
    /// window names exactly as many as there are checks (R16); with three hours
    /// against seven checks the cases stand at the moment they were made, and
    /// the reminder is then the only place «15:30 · 18:00 · 22:00» is written
    /// down. Losing it would cost the person the hours, so this says `false`
    /// and both tiles stay. A practice with no window states no hour at all.
    static func saysEveryHour(_ face: GroupFace, window: TimeWindow?) -> Bool {
        guard let window else { return false }
        var stated: Set<ClockTime> = []
        for mark in face.marks {
            guard let hour = mark.hour else { return false }
            stated.insert(hour)
        }
        return window.hours.allSatisfy { stated.contains($0) }
    }

    /// Collapse a packed row into cells: a group draws once, in the place of
    /// its **first** member. Rank order carries information, so nothing is
    /// reordered to close the hole the other six left (03, packing v0).
    ///
    /// A widget with no `group_id` is a cell of its own — which is what every
    /// widget on an old desk is, and why an old desk draws exactly as before.
    static func cells(_ widgets: [Widget], instances: [Instance], now: Date) -> [LidCell] {
        var cells: [LidCell] = []
        var drawn: Set<String> = []
        for widget in widgets {
            guard let groupId = widget.groupId else {
                cells.append(.single(widget))
                continue
            }
            guard !drawn.contains(groupId) else { continue }
            drawn.insert(groupId)
            guard let face = face(of: groupId, widgets: widgets, instances: instances, now: now),
                  face.total > 1
            else {
                // A group of one is a tile of one. Nothing to collapse, and no
                // «1/1» on the lid for a practice that promised once.
                cells.append(.single(widget))
                continue
            }
            cells.append(.group(face))
        }
        return cells
    }
}

/// One occurrence, as a mark on the group tile.
struct GroupMark: Sendable, Equatable, Identifiable {
    var widgetId: String
    var instanceId: String
    var hour: ClockTime?
    var done: Bool

    var id: String { widgetId }
}

/// What one group tile draws. A picture of the group, not a runtime.
struct GroupFace: Sendable, Equatable, Identifiable {
    var id: String
    var subjectId: String
    var title: String
    var nextHour: ClockTime?
    var done: Int
    var marks: [GroupMark]

    var total: Int { marks.count }

    /// The occurrence the big hour is about — the one a tap on the tile opens.
    /// With everything closed there is nothing left to do, so the tile falls
    /// back to its first mark rather than opening nothing.
    var leadWidgetId: String? {
        if let hour = nextHour, let mark = marks.first(where: { !$0.done && $0.hour == hour }) {
            return mark.widgetId
        }
        return marks.first?.widgetId
    }
}

/// A cell of the lid pack: one widget, or one group drawn once.
enum LidCell: Identifiable {
    case single(Widget)
    case group(GroupFace)

    var id: String {
        switch self {
        case .single(let widget): "w:\(widget.id)"
        case .group(let face): "g:\(face.id)"
        }
    }

    var subjectId: String {
        switch self {
        case .single(let widget): widget.subjectId
        case .group(let face): face.subjectId
        }
    }
}
