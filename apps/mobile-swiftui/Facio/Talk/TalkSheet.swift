import SwiftUI

struct TalkSheet: View {
    @Environment(TalkStore.self) private var talk
    @Environment(DeskStore.self) private var store
    @FocusState private var composerFocused: Bool
    var onOpenSnapshot: (ChatSnapshot) -> Void

    var body: some View {
        @Bindable var talk = talk
        NavigationStack {
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
                            TalkBubble(message: message, onOpenSnapshot: onOpenSnapshot)
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
                // The kebab miniature expands into this sheet standing on the
                // same message — the derived scroll target, not a chapter the
                // user is told about. No anchor: the sheet opens as it always
                // did, at the bottom.
                .onAppear {
                    guard let anchor = talk.anchorMessageId else { return }
                    proxy.scrollTo(anchor, anchor: .center)
                }
            }
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
                TalkComposerBar(talk: talk, focused: $composerFocused) {
                    Task { await send() }
                }
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

    private func send() async {
        if let response = await talk.send(desk: store.snapshot) {
            store.applyTalk(response.desk, toolCalls: response.toolCalls)
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

private struct TalkComposerBar: View {
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

private struct TalkBubble: View {
    let message: ChatMessage
    var onOpenSnapshot: (ChatSnapshot) -> Void

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
                Text(message.text)
                    .font(.body)
                    .foregroundStyle(.primary)
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
