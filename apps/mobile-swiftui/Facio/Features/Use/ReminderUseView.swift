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

    private var deadline: ClockTime? {
        savedClock ?? window?.latestBy
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
                .accessibilityLabel("успеть к \(deadline.shortLabel)")
                .accessibilityHint("открывает выбор времени")
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
                store.editReminderLatestBy(widgetId: edit.widgetId, latestBy: clock)
            }
        }
        .onAppear {
            store.markCueSurfaced(widgetId: widget.id, place: "use")
        }
    }

    private func openPicker() {
        guard let window else { return }
        timeEdit = ReminderTimeEdit(
            widgetId: widget.id,
            window: window,
            start: deadline ?? window.latestBy
        )
    }
}

private struct ReminderTimeEdit: Identifiable {
    var id: String { widgetId }
    let widgetId: String
    let window: TimeWindow
    let start: ClockTime
}

@Observable
@MainActor
private final class ReminderTimeDraft {
    var hour: Int
    var minute: Int

    init(clock: ClockTime) {
        hour = clock.hour
        minute = clock.minute
    }

    var clock: ClockTime {
        ClockTime(hour: hour, minute: minute)
    }
}

private struct ReminderTimePickerSheet: View {
    @Environment(\.dismiss) private var dismiss
    let hours: ClosedRange<Int>
    let onSave: (ClockTime) -> Void
    @State private var draft: ReminderTimeDraft

    init(edit: ReminderTimeEdit, onSave: @escaping (ClockTime) -> Void) {
        self.hours = ReminderClock.gymHourRange(window: edit.window)
        self.onSave = onSave
        let start = ReminderClock.clamp(edit.start, to: edit.window)
        _draft = State(initialValue: ReminderTimeDraft(clock: start))
    }

    var body: some View {
        @Bindable var draft = draft
        VStack(spacing: 0) {
            HStack(spacing: 8) {
                Picker("час", selection: $draft.hour) {
                    ForEach(Array(hours), id: \.self) { value in
                        Text(String(value))
                            .font(.title2.monospacedDigit())
                            .tag(value)
                    }
                }
                .pickerStyle(.wheel)
                .labelsHidden()
                .frame(width: 128, height: 196)
                .accessibilityLabel("час")

                Text(":")
                    .font(.title.weight(.semibold).monospacedDigit())
                    .foregroundStyle(.primary)
                    .accessibilityHidden(true)

                Picker("минуты", selection: $draft.minute) {
                    ForEach(0..<60, id: \.self) { value in
                        Text(String(format: "%02d", value))
                            .font(.title2.monospacedDigit())
                            .tag(value)
                    }
                }
                .pickerStyle(.wheel)
                .labelsHidden()
                .frame(width: 128, height: 196)
                .accessibilityLabel("минуты")
            }
            .frame(maxWidth: .infinity)
            .padding(.top, 4)

            Spacer(minLength: 8)

            Button {
                onSave(draft.clock)
                dismiss()
            } label: {
                Text("Сохранить")
                    .font(.headline)
                    .frame(maxWidth: .infinity, minHeight: 52)
                    .contentShape(Capsule())
            }
            .facioGlassButton(prominent: true, capsule: true)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.bottom, 4)
        .presentationDetents([.height(340)])
        .presentationDragIndicator(.visible)
    }
}
