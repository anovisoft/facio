import SwiftUI

struct LidWidgetCell: View {
    let widget: Widget
    let cue: Cue?
    let onOpen: () -> Void
    let onToggleTick: () -> Void
    let onSurfaced: () -> Void

    var body: some View {
        Group {
            switch widget.type {
            case .counter:
                CounterTile(widget: widget, cue: cue, onOpen: onOpen, onSurfaced: onSurfaced)
            case .tick:
                TickTile(widget: widget, onOpen: onOpen, onToggle: onToggleTick)
            case .checklist, .reminder, .timer, .stepper:
                FacioTileButton(action: onOpen) {
                    Text(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                        .font(.headline)
                        .foregroundStyle(.primary)
                }
            }
        }
        .tileCellSize(TileCells.size(for: widget.tileSize))
    }
}
