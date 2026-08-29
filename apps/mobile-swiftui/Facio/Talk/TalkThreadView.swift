import SwiftUI

/// The thread itself — bubbles, the centered snapshots, the composer — with no
/// opinion about what is holding it.
///
/// The mouth sheet from the lid dock and the kebab's expanded talk are the
/// **same** conversation seen from two places, so they are the same views. The
/// kebab does not invent a second messenger (03-product).
struct TalkThreadScroll: View {
    var onOpenSnapshot: (ChatSnapshot) -> Void
    var onAskAboutPhrase: (String) -> Void

    @Environment(TalkStore.self) private var talk
    /// The anchor has to survive the box growing around it: the kebab miniature
    /// expands into a taller card, and a `scrollTo` issued at the small size
    /// lands in the wrong place once the growing stops. Re-issued on every
    /// height the box passes through, so the last one wins.
    @State private var lastHeight: CGFloat = 0

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    if talk.current.messages.isEmpty {
                        Text(talk.placeholder)
                            .font(.body)
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.top, 8)
                    }
                    ForEach(talk.current.messages) { message in
                        TalkBubble(
                            message: message,
                            onOpenSnapshot: onOpenSnapshot,
                            onAskAboutPhrase: onAskAboutPhrase
                        )
                        .id(message.id)
                    }
                    if talk.sending {
                        ProgressView()
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .id("sending")
                    }
                    if let errorMessage = talk.errorMessage {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                            .id("error")
                    }
                }
                .padding(.horizontal, FacioPalette.pagePadding)
                .padding(.bottom, 12)
            }
            .scrollIndicators(.hidden)
            .onChange(of: talk.current.messages.count) { _, _ in
                scroll(proxy)
            }
            .onChange(of: talk.sending) { _, _ in
                scroll(proxy)
            }
            // The kebab miniature expands onto the same message the picture was
            // showing — the derived scroll target, not a chapter the user is
            // told about. No anchor: the thread opens at the bottom, as always.
            .onAppear {
                guard let anchor = talk.anchorMessageId else { return }
                proxy.scrollTo(anchor, anchor: .center)
            }
            .onGeometryChange(for: CGFloat.self) { proxyGeometry in
                proxyGeometry.size.height
            } action: { height in
                guard height != lastHeight else { return }
                lastHeight = height
                guard let anchor = talk.anchorMessageId else { return }
                proxy.scrollTo(anchor, anchor: .center)
            }
        }
    }

    private func scroll(_ proxy: ScrollViewProxy) {
        if talk.sending {
            proxy.scrollTo("sending", anchor: .bottom)
        } else if let last = talk.current.messages.last {
            proxy.scrollTo(last.id, anchor: .bottom)
        }
    }
}

struct TalkComposerBar: View {
    @Bindable var talk: TalkStore
    var focused: FocusState<Bool>.Binding
    var onSend: () -> Void

    var body: some View {
        HStack(alignment: .center, spacing: 8) {
            TextField(talk.placeholder, text: $talk.draft)
                .font(.body)
                .textFieldStyle(.plain)
                .focused(focused)
                .accessibilityLabel(talk.placeholder)
                .onSubmit(onSend)
            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 32))
                    .symbolRenderingMode(.hierarchical)
            }
            .disabled(talk.sending || talk.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            .accessibilityLabel("Отправить")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .facioGlass()
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.bottom, 8)
    }
}

struct TalkBubble: View {
    let message: ChatMessage
    var onOpenSnapshot: (ChatSnapshot) -> Void
    var onAskAboutPhrase: (String) -> Void

    var body: some View {
        switch message.kind {
        case .user:
            HStack {
                Spacer(minLength: 48)
                Text(message.text)
                    .font(.body)
                    .foregroundStyle(.primary)
                    .padding(12)
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
            }
        case .assistant:
            HStack {
                SelectableAnswerText(text: message.text, onAsk: onAskAboutPhrase)
                    .padding(12)
                    .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))
                Spacer(minLength: 48)
            }
        case .snapshot:
            if let snapshot = message.snapshot {
                SnapshotCard(snapshot: snapshot) {
                    onOpenSnapshot(snapshot)
                }
            }
        }
    }
}

private struct SnapshotCard: View {
    let snapshot: ChatSnapshot
    var onOpen: () -> Void

    var body: some View {
        HStack {
            Spacer(minLength: 24)
            Button(action: onOpen) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: snapshot.subjectId, stored: snapshot.title))
                        .font(.headline)
                        .foregroundStyle(.primary)
                    Text(snapshot.line)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .padding(16)
                .frame(maxWidth: 280, alignment: .leading)
                .contentShape(RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous))
                .facioGlass()
            }
            .buttonStyle(.plain)
            .accessibilityLabel(DisplayCopy.title(subjectId: snapshot.subjectId, stored: snapshot.title))
            Spacer(minLength: 24)
        }
    }
}

/// One turn of the conversation, wherever the person is standing when they take
/// it. Both the lid's sheet and the kebab's expanded talk go through here, so a
/// send from the kebab lands on the desk exactly like a send from the dock.
@MainActor
enum TalkActions {
    static func send(talk: TalkStore, desk: DeskStore) async {
        if let response = await talk.send(desk: desk.snapshot) {
            desk.applyTalk(response.desk, toolCalls: response.toolCalls)
        }
    }

    /// A phrase out of the answer goes back with whatever the client honestly
    /// knows it hangs on — the widget this talk stands over, and nothing
    /// invented. With no binding the mouth owes text and no cue; the desk, not
    /// the client, decides that (05).
    static func ask(quote: String, talk: TalkStore, desk: DeskStore) {
        guard let selection = ClarificationLaw.selection(
            quote: quote,
            focusedWidgetId: talk.focusedWidgetId,
            widgets: desk.snapshot.widgets
        ) else { return }
        Task {
            let response = await talk.send(
                utterance: SelectableAnswerText.askUtterance(quote: selection.quote),
                desk: desk.snapshot,
                selection: selection
            )
            if let response {
                desk.applyTalk(response.desk, toolCalls: response.toolCalls)
            }
        }
    }
}
