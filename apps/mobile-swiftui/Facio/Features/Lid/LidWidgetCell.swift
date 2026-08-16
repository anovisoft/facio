import SwiftUI

struct LidWidgetCell: View {
    let widget: Widget
    let cue: Cue?
    let window: TimeWindow?
    let onOpen: (() -> Void)?
    let onToggleTick: (() -> Void)?
    let onSurfaced: () -> Void

    var body: some View {
        switch widget.type {
        case .counter:
            sized(
                CounterTile(widget: widget, cue: cue, onOpen: onOpen, onSurfaced: onSurfaced)
            )
        case .tick:
            sized(TickTile(widget: widget, onOpen: onOpen, onToggle: onToggleTick))
        case .reminder:
            sized(
                ReminderTile(
                    widget: widget,
                    cue: cue,
                    window: window,
                    onOpen: onOpen,
                    onSurfaced: onSurfaced
                )
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
