import SwiftUI

struct ReminderTile: View {
    let widget: Widget
    let cue: Cue?
    let window: TimeWindow?
    let onOpen: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    private var done: Bool { widget.status == .done }

    /// The hour the tile is asking about now: the nearest one still ahead. With
    /// one hour in the window this is that hour, as it always was (Q34).
    private var deadline: ClockTime? {
        window.map { ReminderClock.nextHour(window: $0, now: Date()) }
    }

    /// The rest of the hours the person named, digits only. Empty for a
    /// single-hour window, which is the ordinary case.
    private var laterHours: [ClockTime] {
        guard let window, let deadline, window.hours.count > 1 else { return [] }
        return window.hoursAfter(deadline)
    }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(done ? .secondary : .primary)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    KebabStub()
                }
                Spacer(minLength: 0)
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    if let deadline {
                        Text(deadline.shortLabel)
                            .font(.system(size: 28, weight: .bold, design: .rounded))
                            .foregroundStyle(done ? .secondary : .primary)
                    }
                    if !laterHours.isEmpty {
                        Text(laterHours.map(\.shortLabel).joined(separator: " "))
                            .font(.caption.monospacedDigit())
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                    if let cue {
                        Text(cue.text)
                            .font(.subheadline.weight(.semibold))
                            .foregroundStyle(done ? .secondary : .primary)
                            .lineLimit(1)
                    }
                    Spacer(minLength: 0)
                }
            }
        }
        .accessibilityLabel(accessibilityLabel)
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    private var accessibilityLabel: String {
        let title = DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title)
        if done {
            return String(localized: "\(title), готово", comment: "Tile accessibility: done")
        }
        let deadline = self.deadline.map(DisplayCopy.succeedBy(clock:))
        return [title, deadline, cue?.text].compactMap { $0 }.joined(separator: ", ")
    }
}
