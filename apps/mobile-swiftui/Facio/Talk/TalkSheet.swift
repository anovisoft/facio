import SwiftUI

/// The almost-fullscreen sheet the lid dock opens. The thread inside it is
/// `TalkThreadScroll`, the same one the kebab expands into — one conversation,
/// two ways in.
struct TalkSheet: View {
    @Environment(TalkStore.self) private var talk
    @Environment(DeskStore.self) private var store
    @FocusState private var composerFocused: Bool
    var onOpenSnapshot: (ChatSnapshot) -> Void

    var body: some View {
        @Bindable var talk = talk
        NavigationStack {
            TalkThreadScroll(
                onOpenSnapshot: onOpenSnapshot,
                onAskAboutPhrase: { TalkActions.ask(quote: $0, talk: talk, desk: store) }
            )
            .navigationTitle("Facio")
            .toolbarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        talk.newChat()
                    } label: {
                        Text("Новый чат")
                    }
                    .disabled(talk.sending)
                    .accessibilityLabel("Новый чат")
                }
            }
            .safeAreaInset(edge: .bottom) {
                TalkComposerBar(
                    talk: talk,
                    focused: $composerFocused,
                    onSend: { Task { await TalkActions.send(talk: talk, desk: store) } },
                    onChip: { TalkActions.send(chip: $0, talk: talk, desk: store) }
                )
            }
        }
        .presentationDetents([.fraction(0.94)])
        .presentationDragIndicator(.visible)
        .onAppear {
            // Arriving on an anchor means the person came to look at that part
            // of the talk; the keyboard would cover it. Everywhere else the
            // sheet still opens ready to type.
            composerFocused = talk.anchorMessageId == nil
        }
    }
}
