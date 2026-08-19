import SwiftUI

struct PanScreen: View {
    var onOpenTalk: (String) -> Void
    var onOpenDeed: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 28) {
            TalksList(onOpen: onOpenTalk)
            DeedsList(onOpen: onOpenDeed)
            Spacer(minLength: 16)
            Text("Настройки")
                .font(.subheadline)
                .foregroundStyle(.tertiary)
                .accessibilityLabel("Настройки, позже")
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 16)
        .padding(.bottom, 24)
        .safeAreaPadding(.top)
        .safeAreaPadding(.bottom)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .contentShape(Rectangle())
    }
}
