import SwiftUI

struct LidWidgetCell: View {
    let widget: Widget
    let cue: Cue?
    let window: TimeWindow?
    let onOpen: (() -> Void)?
    let onToggleTick: (() -> Void)?
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
        case .checklist, .timer, .stepper:
            EmptyView()
        }
    }

    private func sized<Tile: View>(_ tile: Tile) -> some View {
        tile
            .tileCellSize(TileCells.size(for: widget.tileSize))
            .clipped()
    }
}
