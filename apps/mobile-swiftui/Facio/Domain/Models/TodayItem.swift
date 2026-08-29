import Foundation

enum TodayItem: Sendable, Equatable, Identifiable {
    case widget(band: RankBand, widget: Widget)
    case drift(card: DriftCard)
    case delta(card: DeltaCard)

    var id: String {
        switch self {
        case .widget(_, let widget): widget.id
        case .drift(let card): "drift:\(card.subjectId)"
        case .delta(let card): "delta:\(card.subjectId)"
        }
    }

    var kind: String {
        switch self {
        case .widget: "widget"
        case .drift: "drift"
        case .delta: "delta"
        }
    }

    var band: RankBand {
        switch self {
        case .widget(let band, _): band
        case .drift: .driftCard
        case .delta: .unansweredMorning
        }
    }
}
