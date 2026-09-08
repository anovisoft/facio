import SwiftUI

struct ReminderUseView: View {
    let widget: Widget
    let cue: Cue?

    @Environment(DeskStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var timeEdit: ReminderTimeEdit?
    @State private var savedClock: ClockTime?

    private var window: TimeWindow? {
        store.windowFor(subjectId: widget.subjectId)
    }

    /// The chip names the hour the person is being asked about right now: the
    /// nearest one still ahead, not the first of the day (Q34).
    private var deadline: ClockTime? {
        savedClock ?? window.map { ReminderClock.nextHour(window: $0, now: Date()) }
    }

    /// The rest of the day, when the practice named more than one hour. Digits
    /// only — the hours are what the person said, not copy of ours.
    private var laterHours: [ClockTime] {
        guard let window, let deadline, window.hours.count > 1 else { return [] }
        return window.hoursAfter(deadline)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            if let deadline {
                Button(action: openPicker) {
                    HStack(spacing: 8) {
                        Text("успеть к")
                            .font(.body)
                            .foregroundStyle(.primary)
                        Text(deadline.shortLabel)
                            .font(.body.weight(.semibold).monospacedDigit())
                            .foregroundStyle(.primary)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 5)
                            .background(.tertiary.opacity(0.55), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(
                    String(localized: "успеть к \(deadline.shortLabel)", comment: "Reminder window deadline")
                )
                .accessibilityHint("открывает выбор времени")
            }

            if !laterHours.isEmpty {
                Text(laterHours.map(\.shortLabel).joined(separator: "  "))
                    .font(.subheadline.monospacedDigit())
                    .foregroundStyle(.secondary)
            }

            if let cue {
                Text(cue.text)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.primary)
            }

            Spacer()

            Button {
                store.completeReminder(widgetId: widget.id)
                dismiss()
            } label: {
                Text("Готово")
                    .font(.headline)
                    .frame(maxWidth: .infinity, minHeight: 52)
            }
            .facioGlassButton(prominent: true, capsule: true)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.bottom, 8)
        .sheet(item: $timeEdit) { edit in
            ReminderTimePickerSheet(edit: edit) { clock in
                savedClock = clock
                // Editing the hour in front of you moves that hour. The others
                // the person named stay where they are (Q34).
                store.editReminderHour(widgetId: widget.id, from: edit.start, to: clock)
            }
        }
        .onAppear {
            store.markCueSurfaced(widgetId: widget.id, place: "use")
        }
    }

    private func openPicker() {
        guard let window else { return }
        timeEdit = ReminderTimeEdit(
            id: widget.id,
            window: window,
            start: deadline ?? window.latestBy
        )
    }
}
