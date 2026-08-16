import SwiftUI

struct CounterUseView: View {
    let widget: Widget
    let cue: Cue?

    @Environment(DeskStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var cueDraft = ""
    @State private var goalDraft = ""

    private var count: Int { widget.payload.count ?? 0 }
    private var target: Int { widget.payload.target ?? 0 }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack(alignment: .firstTextBaseline, spacing: 8) {
                Text("\(count)")
                    .font(.system(size: 72, weight: .bold, design: .rounded))
                    .foregroundStyle(.primary)
                    .contentTransition(.numericText())
                Text("/")
                    .font(.title2.weight(.semibold))
                    .foregroundStyle(.tertiary)
                TextField("цель", text: $goalDraft)
                    .keyboardType(.numberPad)
                    .textFieldStyle(.plain)
                    .font(.title2.weight(.semibold).width(.condensed))
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: 72)
                    .accessibilityLabel("цель")
                    .onSubmit(commitGoal)
            }

            TextField("подсказка", text: $cueDraft, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.primary)
                .lineLimit(2...4)
                .accessibilityLabel("подсказка")
                .onSubmit(commitCue)

            Text("можно править текст и цель")
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer()

            FacioGlassCluster(spacing: 12) {
                HStack(spacing: 12) {
                    Button {
                        store.tickCounter(widgetId: widget.id, delta: -1)
                    } label: {
                        Image(systemName: "minus")
                            .font(.title2.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .accessibilityLabel("минус")
                    .modifier(FacioGlassButton(prominent: false))

                    Button {
                        store.tickCounter(widgetId: widget.id, delta: 1)
                    } label: {
                        Image(systemName: "plus")
                            .font(.title2.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .accessibilityLabel("плюс")
                    .modifier(FacioGlassButton(prominent: true))
                }
            }

            Button {
                commitCue()
                commitGoal()
                store.completeCounter(widgetId: widget.id)
                dismiss()
            } label: {
                Text("Готово")
                    .font(.headline)
                    .frame(maxWidth: .infinity, minHeight: 52)
            }
            .modifier(FacioGlassButton(prominent: true, capsule: true))
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.bottom, 8)
        .onAppear {
            cueDraft = cue?.text ?? ""
            goalDraft = String(target)
            store.markCueSurfaced(widgetId: widget.id, place: "use")
        }
        .onChange(of: cue?.text) { _, newValue in
            if let newValue { cueDraft = newValue }
        }
    }

    private func commitCue() {
        let trimmed = cueDraft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let cue, !trimmed.isEmpty, trimmed != cue.text else { return }
        store.editCueText(cueId: cue.id, text: trimmed)
    }

    private func commitGoal() {
        guard let goal = Int(goalDraft), goal >= 1 else {
            goalDraft = String(target)
            return
        }
        if goal != target {
            store.editTarget(widgetId: widget.id, goal: goal)
        }
    }
}

private struct FacioGlassButton: ViewModifier {
    var prominent: Bool
    var capsule: Bool = false

    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            if prominent {
                content.buttonStyle(.glassProminent)
            } else {
                content.buttonStyle(.glass)
            }
        } else if capsule {
            content
                .buttonStyle(.borderedProminent)
                .buttonBorderShape(.capsule)
        } else {
            content
                .buttonStyle(.bordered)
                .buttonBorderShape(.roundedRectangle)
        }
    }
}
