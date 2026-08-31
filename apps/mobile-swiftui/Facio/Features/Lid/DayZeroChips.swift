import SwiftUI

/// Day-0 chips, above the composer dock (03-product, «Composer»). They stand
/// only on a desk that has never held a subject, so the first screen says what
/// is spoken here instead of an empty lid and a placeholder.
///
/// A tap fills the mouth's field and opens the sheet — it does not send.
/// Sizing follows the drift chips: system capsules, height 32, hugging text.
struct DayZeroChips: View {
    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk

    var body: some View {
        if store.showsDayZeroChips, !talk.sheetOpen {
            HStack(spacing: 8) {
                ForEach(DayZeroChip.allCases) { chip in
                    Button {
                        talk.startDraft(chip.text)
                    } label: {
                        Text(chip.text)
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(1)
                            .truncationMode(.tail)
                            .frame(maxWidth: 128)
                    }
                    .accessibilityLabel(chip.text)
                    .controlSize(.small)
                    .buttonStyle(.bordered)
                    .buttonBorderShape(.capsule)
                    .frame(height: 32)
                    .fixedSize(horizontal: true, vertical: false)
                }
                Spacer(minLength: 0)
            }
            .padding(.horizontal, FacioPalette.pagePadding)
            .padding(.bottom, 8)
        }
    }
}
