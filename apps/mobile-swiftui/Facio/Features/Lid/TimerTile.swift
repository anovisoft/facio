import SwiftUI

/// A timer on Today / Lifetime may run on the tile (04). The whole square
/// still opens Use; start / pause is an **overlay sibling** of
/// `FacioTileButton`, the same shape as the tick tile's 36pt mark. The face
/// redraws off a `TimelineView`, not off a stored ticking number — the desk
/// only remembers when the run began.
struct TimerTile: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: (() -> Void)?
    let onToggleRun: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    private static let markSize: CGFloat = 36

    private var running: Bool { TimerLaw.isRunning(widget.payload) }
    private var done: Bool { widget.status == .done }

    var body: some View {
        FacioTileButton(dimmed: done, action: onOpen, onLongPress: onKebab) {
            VStack(alignment: .leading, spacing: 10) {
                HStack(alignment: .top, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(done ? .secondary : .primary)
                        .lineLimit(1)
                    Spacer(minLength: 0)
                    KebabStub()
                }
                Spacer(minLength: 0)
                face
                HStack(spacing: 10) {
                    Color.clear.frame(width: Self.markSize, height: Self.markSize)
                    if done {
                        Text(DisplayCopy.tickState(done: true))
                            .font(.caption.weight(.medium))
                            .foregroundStyle(.secondary)
                    } else if let cue {
                        Text(cue.text)
                            .font(.caption.weight(.medium))
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                }
            }
        }
        .overlay(alignment: .bottomLeading) {
            mark
                .padding(.leading, 16)
                .padding(.bottom, 16)
        }
        .accessibilityLabel(
            DisplayCopy.timerAccessibility(
                title: DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title),
                running: running
            )
        )
        .onAppear {
            if cue != nil, !done { onSurfaced() }
        }
    }

    /// While it runs the face redraws every second; standing still it is a
    /// plain label, so a paused tile costs the lid nothing.
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
            .font(.system(size: 34, weight: .bold, design: .rounded))
            .monospacedDigit()
            .foregroundStyle(done ? .secondary : .primary)
    }

    @ViewBuilder
    private var mark: some View {
        let glyph = Image(systemName: running ? "pause.circle.fill" : "play.circle")
            .font(.system(size: Self.markSize))
            .foregroundStyle(running ? .primary : .secondary)
            .frame(width: Self.markSize, height: Self.markSize)
            .contentShape(Rectangle())
        if let onToggleRun {
            Button(action: onToggleRun) { glyph }
                .buttonStyle(.plain)
                .accessibilityLabel(running ? "пауза" : "старт")
        } else {
            // Soon / Postponed: a glance, never a running timer (03, 04).
            glyph.accessibilityHidden(true)
        }
    }
}
