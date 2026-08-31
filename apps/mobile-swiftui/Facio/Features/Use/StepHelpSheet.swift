import SwiftUI

/// What sits behind the `?` on a step: the explanations this practice picked up
/// in talk, each with the phrase that was asked about — and, when the person
/// put one in the conversation, the one media item that explanation carries.
///
/// This is the only place a `clarification` is drawn. Inline at do-time it would
/// turn rep one into a wall of text and P9 would die by drowning (04); the
/// `correction` above the counter stays exactly where it was, and stays text.
/// Media rides its cue's surface, so a video lives here and nowhere else.
///
/// The text is drawn first and unconditionally. Media is an extra that loads
/// beside it: the sheet is complete before anything has come down the wire
/// (04, «a step must be executable without its media»).
struct StepHelpSheet: View {
    let cues: [Cue]

    /// A sheet with a player in it needs the room; one with three sentences in
    /// it does not, and 0.42 is the size that was accepted.
    private var detent: PresentationDetent {
        cues.contains { CueMediaLaw.presentation($0.media) != .none } ? .fraction(0.85) : .fraction(0.42)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("объяснение")
                .font(.headline)
                .foregroundStyle(.secondary)
                .accessibilityAddTraits(.isHeader)
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    ForEach(cues) { cue in
                        VStack(alignment: .leading, spacing: 6) {
                            if let quote = cue.quote, !quote.isEmpty {
                                Text(quote)
                                    .font(.subheadline)
                                    .foregroundStyle(.secondary)
                                    .italic()
                            }
                            Text(cue.text)
                                .font(.body)
                                .foregroundStyle(.primary)
                                .fixedSize(horizontal: false, vertical: true)
                            CueMediaView(media: cue.media)
                                .padding(.top, 4)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.bottom, 12)
            }
            .scrollIndicators(.hidden)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 24)
        .presentationDetents([detent])
        .presentationDragIndicator(.visible)
    }
}
