import SwiftUI

struct LidFeed: View {
    let projection: LidProjection
    let cueFor: (Widget) -> Cue?
    let windowFor: (String) -> TimeWindow?
    let onOpen: (String) -> Void
    let onToggleTick: (String) -> Void
    let onSurfaced: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            section(title: "Сегодня", widgets: todayWidgets)
            if !projection.lifetime.isEmpty {
                section(title: "Lifetime", widgets: projection.lifetime)
            }
            if !projection.soon.isEmpty {
                section(title: "В ближайшее время", widgets: projection.soon)
            }
            if !projection.postponed.isEmpty {
                section(title: "Отложили", widgets: projection.postponed)
            }
        }
    }

    private var todayWidgets: [Widget] {
        projection.today.compactMap { item in
            if case .widget(_, let widget) = item { return widget }
            return nil
        }
    }

    @ViewBuilder
    private func section(title: LocalizedStringKey, widgets: [Widget]) -> some View {
        LidSectionHeader(title: title)
        if widgets.isEmpty {
            Text("ничего на сегодня — и это нормально")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .padding(.vertical, 8)
        } else {
            PackRowMajorLayout(gap: FacioPalette.gridGap) {
                ForEach(widgets) { widget in
                    LidWidgetCell(
                        widget: widget,
                        cue: cueFor(widget),
                        window: windowFor(widget.subjectId),
                        onOpen: { onOpen(widget.id) },
                        onToggleTick: { onToggleTick(widget.id) },
                        onSurfaced: { onSurfaced(widget.id) }
                    )
                }
            }
        }
    }
}
