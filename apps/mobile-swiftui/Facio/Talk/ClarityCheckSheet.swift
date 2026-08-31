import SwiftUI

/// Q32's one check: a method delivered is not a method understood. After the
/// first case closes on a practice the mouth explained, ask once — and only
/// once — whether the explanation landed.
///
/// Two answers, both ordinary replies in the current thread. No third option
/// and no "try harder": this is a check, not a nag (P8).
enum ClarityCheckCopy {
    static var question: String {
        String(localized: "Понятно объяснили или показать иначе?", comment: "Q32 check after the first case")
    }

    static var clear: String {
        String(localized: "понятно", comment: "Q32 answer: the explanation landed")
    }

    static var differently: String {
        String(localized: "показать иначе", comment: "Q32 answer: show it differently")
    }
}

struct ClarityCheckSheet: View {
    var onAnswer: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text(ClarityCheckCopy.question)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.primary)
                .fixedSize(horizontal: false, vertical: true)
            HStack(spacing: 8) {
                chip(ClarityCheckCopy.clear)
                chip(ClarityCheckCopy.differently)
            }
            Spacer(minLength: 0)
        }
        .frame(maxWidth: .infinity, alignment: .topLeading)
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 28)
        .presentationDetents([.fraction(0.3)])
        .presentationDragIndicator(.visible)
    }

    /// System capsules, hugging their text — the drift card's rule, for the
    /// same reason: equal-width buttons across the card read as a form.
    private func chip(_ title: String) -> some View {
        Button {
            onAnswer(title)
        } label: {
            Text(title)
                .font(.subheadline)
                .lineLimit(1)
                .truncationMode(.tail)
                .frame(minHeight: 32)
                .frame(maxWidth: 152)
        }
        .buttonStyle(.bordered)
        .buttonBorderShape(.capsule)
        .accessibilityLabel(title)
    }
}
