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
            todaySection
            packSection("Lifetime", projection.lifetime, opensUse: true)
            packSection("В ближайшее время", projection.soon, opensUse: false)
            packSection("Отложили", projection.postponed, opensUse: false)
        }
    }

    private var todayWidgets: [Widget] {
        projection.today.compactMap { item in
            if case .widget(_, let widget) = item, widget.type.showsOnLid { return widget }
            return nil
        }
    }

    @ViewBuilder
    private var todaySection: some View {
        LidSectionHeader(title: "Сегодня")
        if todayWidgets.isEmpty {
            if projection.today.isEmpty {
                Text("ничего на сегодня — и это нормально")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .padding(.vertical, 8)
            }
        } else {
            pack(todayWidgets, opensUse: true)
        }
    }

    @ViewBuilder
    private func packSection(_ title: LocalizedStringKey, _ widgets: [Widget], opensUse: Bool) -> some View {
        let visible = widgets.filter { $0.type.showsOnLid }
        if !visible.isEmpty {
            LidSectionHeader(title: title)
            pack(visible, opensUse: opensUse)
        }
    }

    private func pack(_ widgets: [Widget], opensUse: Bool) -> some View {
        PackRowMajorLayout(gap: FacioPalette.gridGap) {
            ForEach(widgets) { widget in
                LidWidgetCell(
                    widget: widget,
                    cue: cueFor(widget),
                    window: windowFor(widget.subjectId),
                    onOpen: opensUse ? { onOpen(widget.id) } : nil,
                    onToggleTick: opensUse ? { onToggleTick(widget.id) } : nil,
                    onSurfaced: { onSurfaced(widget.id) }
                )
            }
        }
    }
}
