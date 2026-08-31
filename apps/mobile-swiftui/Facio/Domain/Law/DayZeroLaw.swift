import Foundation

/// Day zero — the very first lid a person opens. 03-product, «Composer»:
/// empty Сегодня, chips above the composer (`today` / `dinner` / `gym`).
///
/// The chips are a way in, not an onboarding wizard. They belong to a desk that
/// has never held a subject; an ordinary empty day on a desk full of practices
/// is not day zero and gets nothing (never-do #15 — do not pad Today).
enum DayZeroLaw {
    /// `closed` is the latch that lives next to `desk.json`. It flips the first
    /// time a subject lands on the desk and never flips back — without it the
    /// chips would blink again on every rest day, and again on a desk the
    /// service handed back empty.
    static func showsChips(subjects: [Subject], closed: Bool) -> Bool {
        !closed && subjects.isEmpty
    }

    /// The first subject closes day zero. Status does not matter: a practice
    /// that was retired still happened.
    static func closes(subjects: [Subject]) -> Bool {
        !subjects.isEmpty
    }
}

/// The three ways in from 03-product. The label is exactly what lands in the
/// mouth's field — the first send stays the person's, we do not speak for him.
enum DayZeroChip: String, CaseIterable, Identifiable {
    case today
    case dinner
    case gym

    var id: String { rawValue }

    var text: String {
        switch self {
        case .today: String(localized: "сегодня", comment: "Day-0 chip: today")
        case .dinner: String(localized: "ужин", comment: "Day-0 chip: dinner")
        case .gym: String(localized: "зал", comment: "Day-0 chip: gym")
        }
    }
}
