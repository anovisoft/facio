import SwiftUI

/// Pins the composer above the home indicator on the current screen.
/// Do not put this on `NavigationStack` — pushed Use does not inherit that inset,
/// and «Готово» sits under the dock.
struct FacioComposerDock: ViewModifier {
    @Environment(TalkStore.self) private var talk

    func body(content: Content) -> some View {
        content.safeAreaInset(edge: .bottom, spacing: 0) {
            if !talk.sheetOpen {
                ComposerDock()
            }
        }
    }
}

extension View {
    func facioComposerDock() -> some View {
        modifier(FacioComposerDock())
    }
}

struct ComposerDock: View {
    @Environment(TalkStore.self) private var talk

    var body: some View {
        Button {
            talk.sheetOpen = true
        } label: {
            HStack(spacing: 12) {
                Text(talk.draft.isEmpty ? talk.placeholder : talk.draft)
                    .font(.body)
                    .foregroundStyle(talk.draft.isEmpty ? .secondary : .primary)
                    .lineLimit(1)
                Spacer(minLength: 0)
                Color.clear
                    .frame(width: 44, height: 44)
                    .accessibilityHidden(true)
            }
            .padding(.leading, 16)
            .padding(.trailing, 8)
            .padding(.vertical, 6)
            .frame(maxWidth: .infinity, minHeight: 52, alignment: .leading)
            .contentShape(RoundedRectangle(cornerRadius: 26, style: .continuous))
            .facioGlass()
        }
        .buttonStyle(.plain)
        .accessibilityLabel(talk.placeholder)
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.bottom, 8)
    }
}
