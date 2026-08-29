import SwiftUI

/// The kebab inspector of 03-product: title, `postpone` / `delete`, the
/// instance carousel with the date above it, `Open`, and the 3×4 chat
/// miniature standing on this instance's last snapshot.
///
/// Not a fourth product: time + life of the object + its talk. `Open` leads to
/// **Inspect**, never to Use.
struct KebabInspector: View {
    let subjectId: String
    var onInspect: (String, String) -> Void
    var onTalk: (TalkAnchor) -> Void
    var onClose: () -> Void

    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @State private var selectedId: String
    @State private var anchor: TalkAnchor?
    @State private var confirmingRemoval = false

    init(
        subjectId: String,
        startingInstanceId: String,
        onInspect: @escaping (String, String) -> Void,
        onTalk: @escaping (TalkAnchor) -> Void,
        onClose: @escaping () -> Void
    ) {
        self.subjectId = subjectId
        self.onInspect = onInspect
        self.onTalk = onTalk
        self.onClose = onClose
        _selectedId = State(initialValue: startingInstanceId)
    }

    var body: some View {
        let now = Date()
        let instances = store.instances(for: subjectId)
        let selected = instances.first { $0.id == selectedId }
        VStack(alignment: .leading, spacing: 14) {
            Text(title)
                .font(.title2.weight(.semibold))
                .foregroundStyle(.primary)
            header
            VStack(spacing: 10) {
                Text(selected.map { DisplayCopy.loudDate($0.when) } ?? "")
                    .font(.headline)
                    .foregroundStyle(.secondary)
                InstanceCarousel(
                    instances: instances,
                    now: now,
                    selectedId: $selectedId,
                    onAdd: add
                )
                Button {
                    onInspect(subjectId, selectedId)
                } label: {
                    Text("Открыть")
                        .font(.headline)
                        .frame(maxWidth: .infinity, minHeight: 52)
                }
                .disabled(selectedId.isEmpty)
                .facioGlassButton(prominent: true, capsule: true)
            }
            .frame(maxWidth: .infinity)
            TalkMiniature(
                messages: previewMessages,
                placeholder: talk.placeholder,
                onExpand: expand
            )
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 20)
        .padding(.bottom, 16)
        .onAppear {
            anchor = talk.anchor(subjectId: subjectId, instanceId: selectedId)
        }
        // Moving the carousel re-resolves the anchor inside the same chat; an
        // instance with no snapshot there leaves the miniature where it stood.
        .onChange(of: selectedId) { _, id in
            anchor = talk.anchor(subjectId: subjectId, instanceId: id, previous: anchor)
        }
        .onChange(of: instances.map(\.id)) { _, ids in
            if selectedId.isEmpty || !ids.contains(selectedId) {
                selectedId = ids.last ?? ""
            }
        }
    }

    private var title: String {
        DisplayCopy.title(
            subjectId: subjectId,
            stored: store.subject(id: subjectId)?.title ?? subjectId
        )
    }

    /// `postpone` and `delete`. Both go through the law and neither is a
    /// punishment: postpone moves the tile to Отложили and silences the alarm,
    /// «Убрать» archives the widget and retires the subject — the instances,
    /// the cues and the talk stay (04-domain-model).
    private var header: some View {
        HStack(spacing: 10) {
            Button {
                store.postpone(subjectId: subjectId)
                onClose()
            } label: {
                Text("Отложить")
                    .font(.subheadline.weight(.medium))
                    .padding(.horizontal, 4)
            }
            .disabled(store.postponeTargets(subjectId: subjectId).isEmpty)
            .facioGlassButton(prominent: false, capsule: true)
            Button {
                confirmingRemoval = true
            } label: {
                Text("Убрать")
                    .font(.subheadline.weight(.medium))
                    .padding(.horizontal, 4)
            }
            .disabled(store.subject(id: subjectId)?.status == .retired)
            .facioGlassButton(prominent: false, capsule: true)
            Spacer(minLength: 0)
        }
        .confirmationDialog(
            "Убрать с крышки?",
            isPresented: $confirmingRemoval,
            titleVisibility: .visible
        ) {
            Button("Убрать", role: .destructive) {
                store.removeFromLid(subjectId: subjectId)
                onClose()
            }
            Button("Отмена", role: .cancel) {}
        } message: {
            Text("Случаи и подсказки останутся.")
        }
    }

    private var previewMessages: [ChatMessage] {
        guard let anchor, let thread = talk.thread(id: anchor.threadId) else { return [] }
        return TalkAnchorLaw.preview(in: thread, anchor: anchor)
    }

    private func expand() {
        onTalk(anchor ?? talk.anchor(subjectId: subjectId, instanceId: selectedId))
    }

    private func add() {
        if let created = store.addInstance(subjectId: subjectId) {
            selectedId = created
        }
    }
}
