import Foundation

struct LidProjection: Sendable, Equatable {
    var today: [TodayItem]
    var lifetime: [Widget]
    var soon: [Widget]
    var postponed: [Widget]
    var driftCard: DriftCard?
    var deltaCard: DeltaCard?
}
