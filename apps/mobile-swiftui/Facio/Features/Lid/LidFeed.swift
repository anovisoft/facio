import SwiftUI

struct LidFeed: View {
    let projection: LidProjection
    let cueFor: (Widget) -> Cue?
    let windowFor: (String) -> TimeWindow?
    let subjectTitle: (String) -> String
    let showsSubject: (String) -> Bool
    let surfacesDrift: (DriftCard) -> Bool
    let onOpen: (String) -> Void
    let onInspect: (String, String) -> Void
    let onKebab: (String) -> Void
    let onToggleTick: (String) -> Void
    let onSurfaced: (String) -> Void
    let onAnswerDrift: (String, DriftOffer) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            todaySection
            packSection("Lifetime", projection.lifetime, opensUse: true)
            packSection("В ближайшее время", projection.soon, opensUse: false)
            packSection("Отложили", projection.postponed, opensUse: false)
        }
    }

    /// Resolve the card from the projection, never from `visibleToday` —
    /// that getter hides the drifting subject's tiles and would recurse.
    private var surfacedCard: DriftCard? {
        projection.today.compactMap { item -> DriftCard? in
            if case .drift(let card) = item, surfacesDrift(card) { return card }
            return nil
        }.first
    }

    private var visibleToday: [TodayItem] {
        let hiddenSubject = surfacedCard?.subjectId
        return projection.today.compactMap { item in
            switch item {
            case .widget(_, let widget):
                if showsWidget(widget, hiding: hiddenSubject) { return item }
                return nil
            case .drift(let card):
                if surfacesDrift(card) { return item }
                return nil
            }
        }
    }

    @ViewBuilder
    private var todaySection: some View {
        LidSectionHeader(title: "Сегодня")
        if visibleToday.isEmpty {
            Text("ничего на сегодня — и это нормально")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .padding(.vertical, 8)
        } else {
            ForEach(todayBlocks(visibleToday)) { block in
                switch block {
                case .pack(_, let widgets):
                    pack(widgets, opensUse: true)
                case .drift(let card):
                    DriftTile(
                        card: card,
                        storedTitle: subjectTitle(card.subjectId),
                        onAnswer: { onAnswerDrift(card.subjectId, $0) }
                    )
                }
            }
        }
    }

    @ViewBuilder
    private func packSection(_ title: LocalizedStringKey, _ widgets: [Widget], opensUse: Bool) -> some View {
        let visible = widgets.filter { showsWidget($0, hiding: surfacedCard?.subjectId) }
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
                    onOpen: {
                        if opensUse {
                            onOpen(widget.id)
                        } else {
                            onInspect(widget.subjectId, widget.instanceId)
                        }
                    },
                    onToggleTick: opensUse ? { onToggleTick(widget.id) } : nil,
                    onKebab: { onKebab(widget.subjectId) },
                    onSurfaced: { onSurfaced(widget.id) }
                )
            }
        }
    }

    private func showsWidget(_ widget: Widget, hiding subjectId: String?) -> Bool {
        guard widget.type.showsOnLid, showsSubject(widget.subjectId) else { return false }
        if let subjectId, widget.subjectId == subjectId { return false }
        return true
    }

    private func todayBlocks(_ items: [TodayItem]) -> [TodayBlock] {
        var blocks: [TodayBlock] = []
        var buffer: [Widget] = []
        func flush() {
            guard !buffer.isEmpty else { return }
            let ids = buffer.map(\.id).joined(separator: ",")
            blocks.append(.pack(ids: ids, widgets: buffer))
            buffer = []
        }
        for item in items {
            switch item {
            case .widget(_, let widget):
                buffer.append(widget)
            case .drift(let card):
                flush()
                blocks.append(.drift(card))
            }
        }
        flush()
        return blocks
    }
}

private enum TodayBlock: Identifiable {
    case pack(ids: String, widgets: [Widget])
    case drift(DriftCard)

    var id: String {
        switch self {
        case .pack(let ids, _): "pack:\(ids)"
        case .drift(let card): "drift:\(card.subjectId)"
        }
    }
}
