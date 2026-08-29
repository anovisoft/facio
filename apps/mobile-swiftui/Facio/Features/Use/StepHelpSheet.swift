import SwiftUI

/// What sits behind the `?` on a step: the explanations this practice picked up
/// in talk, each with the phrase that was asked about.
///
/// This is the only place a `clarification` is drawn. Inline at do-time it would
/// turn rep one into a wall of text and P9 would die by drowning (04); the
/// `correction` above the counter stays exactly where it was.
struct StepHelpSheet: View {
    let cues: [Cue]

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
        .presentationDetents([.fraction(0.42)])
        .presentationDragIndicator(.visible)
    }
}
