import SwiftUI

/// The talk block of the kebab inspector, in both of its states.
///
/// 03-product: «Tap input / tap miniature / swipe the chat region **up** →
/// same almost-fullscreen sheet (expand animation). Header down → back to
/// miniature.» One card, one thread, one place — the block **grows where it
/// stands**. The old route closed the kebab and opened a second sheet, which is
/// the break in perception the PO reported; there is no second sheet any more.
///
/// R18 finishes the thought. Collapsed it is a card and stays one. Expanded it
/// **stops being a card**: the border, the corner radius and the card's own
/// glass go out on the way up, along the same animation that carries the size,
/// so the content ends up flush against the sheet — one surface with one top
/// edge and one grab handle, and no moment in the middle of the gesture where
/// two of them are legible at once.
struct KebabTalkPane: View {
    /// The picture the collapsed card draws — the tail of the talk up to this
    /// instance's last snapshot.
    let messages: [ChatMessage]
    let expanded: Bool
    /// 0 — a card, 1 — the sheet. Interpolated frame by frame (see
    /// `SurfaceMerge`), never read as a flag.
    var expansion: CGFloat
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
    /// Below the sheet's own grab indicator.
    private static let handleRoom: CGFloat = 18
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
        .modifier(SurfaceMerge(progress: expansion))
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
                TalkComposerBar(
                    talk: talk,
                    focused: $composerFocused,
                    onSend: { Task { await TalkActions.send(talk: talk, desk: store) } },
                    onChip: { TalkActions.send(chip: $0, talk: talk, desk: store) }
                )
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
        // The pane is flush with the sheet now, and the sheet draws its grab
        // handle over the top of it. Clear it rather than inset the whole card,
        // which would put a second top edge back on screen.
        .padding(.top, Self.handleRoom)
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

/// A card on the way to being the sheet itself.
///
/// `Animatable` is the point: SwiftUI interpolates `animatableData` and calls
/// `body` on every frame of the transaction, so the border width, the border
/// opacity, the corner radius and the card's glass all move **with** the size.
/// Read off a plain `Bool` they would be re-evaluated once and snap at the end
/// of the gesture — which is exactly the two-layer middle the PO reported.
private struct SurfaceMerge: ViewModifier, Animatable {
    var progress: CGFloat

    nonisolated var animatableData: CGFloat {
        get { progress }
        set { progress = newValue }
    }

    /// The chrome is spent over the **first half** of the movement, not spread
    /// across all of it. Halfway up, a card that still has a border and a
    /// material is a second surface inside the sheet — which is what the PO
    /// saw. Gone by the midpoint, the rest of the growth is content arriving on
    /// the sheet's own surface. It still goes out with the gesture: this is a
    /// steeper ramp, not a jump.
    static func card(at progress: CGFloat) -> CGFloat {
        max(0, min(1, 1 - progress * 2))
    }

    func body(content: Content) -> some View {
        let card = Self.card(at: progress)
        let shape = RoundedRectangle(
            cornerRadius: FacioPalette.tileRadius * card,
            style: .continuous
        )
        content
            // The card's own material, on its own layer so it can be faded.
            // Expanded there is nothing left of it and the sheet's surface is
            // what shows through.
            .background {
                Color.clear
                    .facioGlass(interactive: false)
                    .opacity(card)
                    .allowsHitTesting(false)
            }
            .clipShape(shape)
            .overlay {
                shape.strokeBorder(Color.primary.opacity(0.10 * card), lineWidth: card)
            }
    }
}
