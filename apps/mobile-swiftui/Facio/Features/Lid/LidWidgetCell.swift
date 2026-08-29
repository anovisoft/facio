import SwiftUI

struct LidWidgetCell: View {
    let widget: Widget
    let cue: Cue?
    let window: TimeWindow?
    let onOpen: (() -> Void)?
    let onToggleTick: (() -> Void)?
    let onToggleItem: ((String) -> Void)?
    let onToggleTimer: (() -> Void)?
    let onKebab: () -> Void
    let onSurfaced: () -> Void

    var body: some View {
        switch widget.type {
        case .counter:
            sized(
                CounterTile(widget: widget, cue: cue, onOpen: onOpen, onKebab: onKebab, onSurfaced: onSurfaced)
                    .facioKebab(onKebab)
            )
        case .tick:
            sized(
                TickTile(widget: widget, onOpen: onOpen, onToggle: onToggleTick, onKebab: onKebab)
                    .facioKebab(onKebab)
            )
        case .reminder:
            sized(
                ReminderTile(
                    widget: widget,
                    cue: cue,
                    window: window,
                    onOpen: onOpen,
                    onKebab: onKebab,
                    onSurfaced: onSurfaced
                )
                .facioKebab(onKebab)
            )
        case .checklist:
            sized(
                ChecklistTile(
                    widget: widget,
                    cue: cue,
                    onOpen: onOpen,
                    onToggleItem: onToggleItem,
                    onKebab: onKebab,
                    onSurfaced: onSurfaced
                )
                .facioKebab(onKebab)
            )
        case .timer:
            sized(
                TimerTile(
                    widget: widget,
                    cue: cue,
                    onOpen: onOpen,
                    onToggleRun: onToggleTimer,
                    onKebab: onKebab,
                    onSurfaced: onSurfaced
                )
                .facioKebab(onKebab)
            )
        case .stepper:
            // Not a live stepper on the lid (04): the tile only opens Use.
            sized(
                StepperTile(widget: widget, cue: cue, onOpen: onOpen, onKebab: onKebab, onSurfaced: onSurfaced)
                    .facioKebab(onKebab)
            )
        }
    }

    private func sized<Tile: View>(_ tile: Tile) -> some View {
        tile
            .tileCellSize(TileCells.size(for: widget.tileSize))
            .clipped()
    }
}
