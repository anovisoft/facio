import SwiftUI

/// Use for a checklist: the whole list, one tap per line, «Готово» in the same
/// glass capsule the counter has. No instance carousel and no horizontal swipe
/// — that edge is back (never-do #17, #19). The system bar stays.
struct ChecklistUseView: View {
    let widget: Widget
    let cue: Cue?

    @Environment(DeskStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    private var items: [ChecklistItem] { ChecklistLaw.items(of: widget.payload) }
    private var progress: (done: Int, total: Int) { ChecklistLaw.progress(of: widget.payload) }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            if let cue {
                // The reason, at do-time, on the widget itself (P9). Not a
                // settings screen, not the transcript.
                Text(cue.text)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Text(DisplayCopy.counterFace(count: progress.done, goal: progress.total))
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(.secondary)
                .contentTransition(.numericText())

            ScrollView {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(items) { item in
                        Button {
                            store.toggleChecklistItem(widgetId: widget.id, itemId: item.id)
                        } label: {
                            HStack(spacing: 12) {
                                Image(systemName: item.done ? "checkmark.circle.fill" : "circle")
                                    .font(.system(size: 28))
                                    .foregroundStyle(item.done ? .primary : .secondary)
                                    .frame(width: 44, height: 44)
                                Text(item.text)
                                    .font(.body)
                                    .foregroundStyle(item.done ? .secondary : .primary)
                                    .strikethrough(item.done, color: .secondary)
                                    .multilineTextAlignment(.leading)
                                Spacer(minLength: 0)
                            }
                            .contentShape(Rectangle())
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(DisplayCopy.checklistItemAccessibility(item.text))
                        .accessibilityValue(DisplayCopy.tickState(done: item.done))
                    }
                }
            }
            .scrollBounceBehavior(.basedOnSize)

            Spacer(minLength: 0)

            Button {
                store.completeChecklist(widgetId: widget.id)
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
        .onAppear {
            store.markCueSurfaced(widgetId: widget.id, place: "use")
        }
    }
}
