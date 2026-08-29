import SwiftUI

/// Use for a timer: the face, one start / pause control in the glass capsule,
/// and «Готово» where the counter keeps it. No instance carousel and no
/// horizontal swipe — that edge is back (never-do #17, #19).
struct TimerUseView: View {
    let widget: Widget
    let cue: Cue?

    @Environment(DeskStore.self) private var store
    @Environment(\.dismiss) private var dismiss

    private var running: Bool { TimerLaw.isRunning(widget.payload) }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            if let cue {
                Text(cue.text)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }

            face

            Text(DisplayCopy.timerOf(TimerLaw.face(widget.payload.seconds ?? 0)))
                .font(.caption)
                .foregroundStyle(.secondary)

            Spacer()

            FacioGlassCluster(spacing: 12) {
                HStack(spacing: 12) {
                    Button {
                        store.toggleTimerRun(widgetId: widget.id)
                    } label: {
                        Image(systemName: running ? "pause.fill" : "play.fill")
                            .font(.title2.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .accessibilityLabel(running ? "пауза" : "старт")
                    .facioGlassButton(prominent: true)

                    Button {
                        store.resetTimer(widgetId: widget.id)
                    } label: {
                        Image(systemName: "arrow.counterclockwise")
                            .font(.title2.weight(.semibold))
                            .frame(maxWidth: .infinity, minHeight: 56)
                    }
                    .accessibilityLabel("сначала")
                    .facioGlassButton(prominent: false)
                }
            }

            Button {
                store.completeTimer(widgetId: widget.id)
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

    @ViewBuilder
    private var face: some View {
        if running {
            TimelineView(.periodic(from: .now, by: 1)) { context in
                faceText(at: context.date)
            }
        } else {
            faceText(at: .now)
        }
    }

    private func faceText(at moment: Date) -> some View {
        Text(TimerLaw.face(TimerLaw.remaining(widget.payload, now: moment)))
            .font(.system(size: 72, weight: .bold, design: .rounded))
            .monospacedDigit()
            .foregroundStyle(.primary)
    }
}
