import SwiftUI

/// The stepper tile is **not** a live stepper (04): no beat buttons, nothing
/// to press by accident while the lid scrolls. It shows where the sequence
/// stands and the beat that is next; the tap opens Use, where the buttons are.
struct StepperTile: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    private var beats: [String] { StepperLaw.beats(of: widget.payload) }
    private var position: Int { StepperLaw.position(of: widget.payload) }
    private var done: Bool { widget.status == .done }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 8) {
                HStack(alignment: .top, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(done ? .secondary : .primary)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    Text(DisplayCopy.counterFace(count: position + 1, goal: beats.count))
                        .font(.subheadline.weight(.semibold).width(.condensed))
                        .foregroundStyle(.secondary)
                        .padding(.trailing, 28)
                    KebabStub()
                }
                if let cue, !done {
                    Text(cue.text)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                        .lineLimit(1)
                }
                Spacer(minLength: 0)
                if done {
                    Text(DisplayCopy.tickState(done: true))
                        .font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                } else if let beat = StepperLaw.beat(of: widget.payload) {
                    Text(beat)
                        .font(.body)
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .accessibilityLabel(
            DisplayCopy.stepperAccessibility(
                title: DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title),
                step: position + 1,
                total: beats.count
            )
        )
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }
}
