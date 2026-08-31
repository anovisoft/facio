import SwiftUI

/// The talk block of the kebab inspector, in both of its states.
///
/// 03-product: «Tap input / tap miniature / swipe the chat region **up** →
/// same almost-fullscreen sheet (expand animation). Header down → back to
/// miniature.» One card, one thread, one place — the block **grows where it
/// stands**. The old route closed the kebab and opened a second sheet, which is
/// the break in perception the PO reported; there is no second sheet any more.
struct KebabTalkPane: View {
    /// The picture the collapsed card draws — the tail of the talk up to this
    /// instance's last snapshot.
    let messages: [ChatMessage]
    let expanded: Bool
    var onExpand: () -> Void
    var onCollapse: () -> Void
    var onOpenSnapshot: (ChatSnapshot) -> Void

    @Environment(TalkStore.self) private var talk
    @Environment(DeskStore.self) private var store
    @FocusState private var composerFocused: Bool
    /// The swipe up already answered this touch; the button under it must not
    /// answer it a second time.
    @State private var tapLock = TapLock()

    private static let shape = RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous)
    /// The card grows for about a third of a second. The picture leaves early
    /// and the thread arrives a beat later, so the two never sit on top of each
    /// other as doubled text — the growing is the animation, not a dissolve.
    private static let pictureOut = AnyTransition.opacity.animation(.easeOut(duration: 0.10))
    private static let threadIn = AnyTransition.opacity.animation(.easeIn(duration: 0.18).delay(0.10))

    var body: some View {
        ZStack {
            if expanded {
                talkFullscreen
            } else {
                miniature
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .facioGlass()
        .clipShape(Self.shape)
        // Glass with nothing behind it does not read: the sheet has no
        // atmosphere, so the card needs its own edge to look like a card.
        .overlay(
            Self.shape.strokeBorder(Color.primary.opacity(0.10), lineWidth: 1)
        )
    }

    // MARK: - Collapsed

    private var miniature: some View {
        Button {
            guard tapLock.shouldRunTap() else { return }
            onExpand()
        } label: {
            TalkMiniature(messages: messages, placeholder: talk.placeholder)
                .contentShape(Self.shape)
        }
        .buttonStyle(.plain)
        // Swipe the chat region up — the same expansion as the tap, and it
        // carries all the way to the full height instead of bouncing back.
        .simultaneousGesture(
            DragGesture(minimumDistance: 20)
                .onEnded { value in
                    guard value.translation.height < -20 else { return }
                    tapLock.consume()
                    onExpand()
                }
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Разговор")
        .accessibilityHint("открывает разговор")
        .accessibilityAddTraits(.isButton)
        .transition(.asymmetric(insertion: Self.threadIn, removal: Self.pictureOut))
    }

    // MARK: - Expanded

    private var talkFullscreen: some View {
        VStack(spacing: 0) {
            header
            TalkThreadScroll(
                onOpenSnapshot: onOpenSnapshot,
                onAskAboutPhrase: { TalkActions.ask(quote: $0, talk: talk, desk: store) }
            )
            .safeAreaInset(edge: .bottom) {
                TalkComposerBar(talk: talk, focused: $composerFocused) {
                    Task { await TalkActions.send(talk: talk, desk: store) }
                }
            }
        }
        .transition(.asymmetric(insertion: Self.threadIn, removal: Self.pictureOut))
        .onAppear {
            // The person came to look at a message; the keyboard would cover
            // it. With nothing to stand on the talk opens ready to type, the
            // same way the lid's sheet does.
            composerFocused = talk.anchorMessageId == nil
        }
    }

    /// The header of 03-product: pull it **down** and the talk goes back to
    /// being a miniature. «Новый чат» sits at the top right, as it does in the
    /// lid's sheet — never-do #18 does not care which way in was used.
    private var header: some View {
        HStack(spacing: 8) {
            Button(action: onCollapse) {
                Image(systemName: "chevron.down")
                    .font(.subheadline.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 44, height: 44)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Свернуть разговор")
            Spacer(minLength: 0)
            Button {
                talk.newChat()
            } label: {
                Text("Новый чат")
                    .font(.subheadline.weight(.medium))
            }
            .buttonStyle(.plain)
            .disabled(talk.sending)
            .accessibilityLabel("Новый чат")
        }
        .padding(.horizontal, 12)
        .padding(.top, 4)
        .frame(maxWidth: .infinity)
        .contentShape(Rectangle())
        .gesture(
            DragGesture(minimumDistance: 12)
                .onEnded { value in
                    guard value.translation.height > 24 else { return }
                    onCollapse()
                }
        )
    }
}
