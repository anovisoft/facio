import Foundation

struct Horizon: Sendable, Equatable {
    /// Exactly seven consecutive days from origin.
    var days: [DayStrip]
    /// Unique calendar days strictly after the seventh day that already have a real instance.
    var later: [Date]
}
