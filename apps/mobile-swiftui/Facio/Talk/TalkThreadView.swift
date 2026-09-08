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
    @Environment(DeskStore.self) private var desk
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
                        // The control rides **inside** the message's own cell,
                        // not after it: the thread scrolls to `messages.last`,
                        // and a row appended beside that target lands under the
                        // composer where nobody can reach it.
                        VStack(alignment: .leading, spacing: 8) {
                            TalkBubble(
                                message: message,
                                onOpenSnapshot: onOpenSnapshot,
                                onAskAboutPhrase: onAskAboutPhrase
                            )
                            // P6: a visible mutation is reversible, and the place
                            // it is visible is right here. Under the **last**
                            // message of that turn — normally the centered
                            // snapshot — and only ever that one turn.
                            if message.id == undoAnchorId {
                                TalkUndoControl {
                                    TalkActions.undo(talk: talk, desk: desk)
                                }
                            }
                        }
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

    /// The message the offer hangs under: the last one of the turn the desk is
    /// still holding a step back for. `nil` everywhere else, including the
    /// moment after the person takes it.
    private var undoAnchorId: String? {
        guard let record = desk.undoableTurn, record.threadId == talk.current.id else { return nil }
        return talk.current.messages.last { $0.turnId == record.turnId && !$0.isUndone }?.id
    }

    private func scroll(_ proxy: ScrollViewProxy) {
        if talk.sending {
            proxy.scrollTo("sending", anchor: .bottom)
        } else if let last = talk.current.messages.last {
            proxy.scrollTo(last.id, anchor: .bottom)
        }
    }
}

/// The row of ready replies, and the field. One view, so every way into the
/// talk — the sheet from the lid dock, the kebab expanded in place — gets the
/// row in the one position 03 puts it: **above the composer**, never inside it.
struct TalkComposerBar: View {
    @Bindable var talk: TalkStore
    var focused: FocusState<Bool>.Binding
    var onSend: () -> Void
    /// A chip tapped. It sends that text as the person's own reply, which is
    /// the whole of what a chip is (Q35) — so the caller hands over the same
    /// action typing would take, and nothing chip-shaped exists downstream.
    var onChip: (String) -> Void = { _ in }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ReplyChipsRow(chips: talk.replyChips, disabled: talk.sending, onTap: onChip)
            field
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.bottom, 8)
    }

    private var field: some View {
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
    }
}

/// Q35. One to three sentences the person is about to say, offered by the turn
/// that is on screen.
///
/// A chip is **text**: tapping it sends that sentence as their own reply and
/// the turn proceeds like any typed one. There is no id here and no action —
/// the moment a chip carries one it stops being a shortcut through typing and
/// becomes a button that decides for them (06 AI #2).
///
/// It scrolls rather than wraps: three sentences can be long in either
/// language, and a row that grows to two lines pushes the field down the screen
/// as the answer arrives. Sizing follows the drift chips and day-0 chips —
/// system capsules, height 32, hugging their text — because a fourth kind of
/// chip is a fourth thing to recognise.
struct ReplyChipsRow: View {
    let chips: [String]
    var disabled: Bool = false
    let onTap: (String) -> Void

    var body: some View {
        if !chips.isEmpty {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(chips, id: \.self) { chip in
                        Button {
                            onTap(chip)
                        } label: {
                            Text(chip)
                                .font(.subheadline.weight(.semibold))
                                .lineLimit(1)
                                .truncationMode(.tail)
                                .frame(maxWidth: 200)
                        }
                        .accessibilityLabel(chip)
                        .controlSize(.small)
                        .buttonStyle(.bordered)
                        .buttonBorderShape(.capsule)
                        .frame(height: 32)
                        .fixedSize(horizontal: true, vertical: false)
                        .disabled(disabled)
                    }
                }
                .padding(.horizontal, 2)
            }
            .scrollClipDisabled()
        }
    }
}

/// «Отменить» under the change it takes back. A person's control, leading-aligned
/// like the answer it follows — not a tool the mouth can reach, and not a stack:
/// the desk hands out exactly one of these at a time.
private struct TalkUndoControl: View {
    var onUndo: () -> Void

    var body: some View {
        HStack {
            Button(action: onUndo) {
                Label {
                    Text("Отменить")
                } icon: {
                    Image(systemName: "arrow.uturn.backward")
                }
                .font(.footnote)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)
            .accessibilityLabel(Text("Отменить"))
            Spacer(minLength: 0)
        }
        .padding(.leading, 4)
    }
}

struct TalkBubble: View {
    let message: ChatMessage
    var onOpenSnapshot: (ChatSnapshot) -> Void
    var onAskAboutPhrase: (String) -> Void

    var body: some View {
        content
            // Nothing leaves the thread when a turn is taken back — it goes
            // quiet. The words are still readable; they just stopped being true
            // about the desk.
            .opacity(message.isUndone ? 0.5 : 1)
    }

    @ViewBuilder
    private var content: some View {
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
                SnapshotCard(snapshot: snapshot, undone: message.isUndone) {
                    onOpenSnapshot(snapshot)
                }
            }
        }
    }
}

/// A picture of a widget at write time — drawn from the card, never from the
/// desk as it stands now (04). The sentence under the title is built here, out
/// of this client's catalog: the service sends state, not copy
/// (`SnapshotFaceLaw`).
private struct SnapshotCard: View {
    let snapshot: ChatSnapshot
    /// The turn behind this picture was taken back. The card stays — it is what
    /// was written that day — and says so.
    var undone: Bool = false
    var onOpen: () -> Void

    private var line: String { SnapshotFaceLaw.line(snapshot) }

    var body: some View {
        HStack {
            Spacer(minLength: 24)
            Button(action: onOpen) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(DisplayCopy.title(subjectId: snapshot.subjectId, stored: snapshot.title))
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .strikethrough(undone)
                    if !line.isEmpty {
                        Text(line)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    if undone {
                        Text("Отменено")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .padding(16)
                .frame(maxWidth: 280, alignment: .leading)
                .contentShape(RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous))
                .facioGlass()
            }
            .buttonStyle(.plain)
            .accessibilityLabel(
                [
                    DisplayCopy.title(subjectId: snapshot.subjectId, stored: snapshot.title),
                    line,
                    undone ? String(localized: "Отменено", comment: "An undone talk turn in the thread") : "",
                ]
                .filter { !$0.isEmpty }
                .joined(separator: ", ")
            )
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
            desk.applyTalk(response.desk, toolCalls: response.toolCalls, turn: talk.lastTurn)
        }
    }

    /// A chip tapped, which is the person replying in their own words — the
    /// same path `send` takes, on purpose. If a chip ever needed its own route
    /// through the client it would have stopped being a reply.
    static func send(chip: String, talk: TalkStore, desk: DeskStore) {
        Task {
            if let response = await talk.send(utterance: chip, desk: desk.snapshot) {
                desk.applyTalk(response.desk, toolCalls: response.toolCalls, turn: talk.lastTurn)
            }
        }
    }

    /// The one step back, pressed by the person under the change it takes back.
    /// The desk restores the structure and keeps the progress; the thread keeps
    /// the words and marks them undone. Two stores, one action, no third place
    /// where «what was undone» is decided.
    static func undo(talk: TalkStore, desk: DeskStore) {
        guard let record = desk.undoLastTalk() else { return }
        talk.markUndone(threadId: record.threadId, turnId: record.turnId)
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
                desk.applyTalk(response.desk, toolCalls: response.toolCalls, turn: talk.lastTurn)
            }
        }
    }
}
