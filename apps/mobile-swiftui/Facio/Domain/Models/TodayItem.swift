import Foundation

enum TodayItem: Sendable, Equatable, Identifiable {
    case widget(band: RankBand, widget: Widget)
    case drift(card: DriftCard)

    var id: String {
        switch self {
        case .widget(_, let widget): widget.id
        case .drift(let card): "drift:\(card.subjectId)"
        }
    }

    var kind: String {
        switch self {
        case .widget: "widget"
        case .drift: "drift"
        }
    }

    var band: RankBand {
        switch self {
        case .widget(let band, _): band
        case .drift: .driftCard
        }
    }
}
