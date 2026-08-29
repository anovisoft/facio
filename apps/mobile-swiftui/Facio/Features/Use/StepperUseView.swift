import SwiftUI

/// Use for a stepper. 03 «Two fullscreens» puts this type's buttons **at the
/// bottom**, so the beat is read at the top and the hands work below it. No
/// instance carousel and no horizontal swipe — that edge is back
/// (never-do #17, #19); «дальше» is a button, never a page turn.
struct StepperUseView: View {
    let widget: Widget
    let cue: Cue?

    @Environment(DeskStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    private var beats: [String] { StepperLaw.beats(of: widget.payload) }
    private var position: Int { StepperLaw.position(of: widget.payload) }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            if let cue {
                Text(cue.text)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            Text(DisplayCopy.counterFace(count: position + 1, goal: beats.count))
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundStyle(.secondary)
                .contentTransition(.numericText())

            Text(StepperLaw.beat(of: widget.payload) ?? "")
                .font(.title2.weight(.semibold))
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
                .accessibilityLabel(
                    DisplayCopy.stepperAccessibility(
                        title: StepperLaw.beat(of: widget.payload) ?? "",
                        step: position + 1,
                        total: beats.count
                    )
                )

            Spacer()

            FacioGlassCluster(spacing: 12) {
                HStack(spacing: 12) {
                    Button {
                        store.stepBack(widgetId: widget.id)
                    } label: {
                        Image(systemName: "chevron.left")
                            .font(.title2.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .accessibilityLabel("назад")
                    .facioGlassButton(prominent: false)
                    .opacity(StepperLaw.isFirst(widget.payload) ? 0.4 : 1)

                    Button {
                        store.stepForward(widgetId: widget.id)
                    } label: {
                        Image(systemName: "chevron.right")
                            .font(.title2.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .accessibilityLabel("дальше")
                    .facioGlassButton(prominent: true)
                    .opacity(StepperLaw.isLast(widget.payload) ? 0.4 : 1)
                }
            }

            Button {
                store.completeStepper(widgetId: widget.id)
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
