import Foundation

enum PainLaw {
    private static let needles = [
        "боль",
        "болит",
        "больно",
        "hurts",
        "hurt",
        "pain",
        "травм",
        "поясниц",
    ]

    static func reportsPain(_ utterance: String) -> Bool {
        let text = utterance.lowercased()
        return needles.contains { text.contains($0) }
    }
}
