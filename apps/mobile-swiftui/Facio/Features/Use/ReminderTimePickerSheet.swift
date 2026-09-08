import SwiftUI

/// The hour picker the PO accepted on Use: a ~340pt bottom sheet, two wide
/// wheels with a colon, **Сохранить** pinned to the bottom, no title and no
/// atmosphere of its own.
///
/// It lives in its own file because it now has a second caller. R17 hid the
/// reminder tile whenever the group already says every hour, so the kebab
/// carousel became the only place left where a person can add, move or drop
/// one — and a second wheel would be a second answer to a question that was
/// already answered (`docs/state`: no `DatePicker`, no `.medium`, no inline
/// wheel). Same view, two ways in.
struct ReminderTimeEdit: Identifiable {
    /// Whatever the caller re-opens the sheet on: the reminder widget on Use,
    /// the case being edited in the carousel, or the `+` that has no case yet.
    let id: String
    let window: TimeWindow
    let start: ClockTime
}

@Observable
@MainActor
final class ReminderTimeDraft {
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

struct ReminderTimePickerSheet: View {
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
