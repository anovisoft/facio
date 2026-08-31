import SwiftUI

struct PanScreen: View {
    var onOpenTalk: (String) -> Void
    var onOpenDeed: (String) -> Void
    var onOpenSettings: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 28) {
            TalksList(onOpen: onOpenTalk)
            DeedsList(onOpen: onOpenDeed)
            Spacer(minLength: 16)
            Button(action: onOpenSettings) {
                HStack(spacing: 8) {
                    Image(systemName: "gearshape")
                    Text("Настройки")
                    Spacer(minLength: 0)
                }
                .font(.headline)
                .foregroundStyle(.primary)
                .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 16)
        .padding(.bottom, 24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .contentShape(Rectangle())
    }
}
