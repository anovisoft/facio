import SwiftUI

/// The kebab inspector of 03-product: title, `postpone` / `delete`, the
/// instance carousel with the date above it, `Open`, and the 3×4 chat
/// miniature standing on this instance's last snapshot.
///
/// Not a fourth product: time + life of the object + its talk. `Open` leads to
/// **Inspect**, never to Use.
///
/// The talk **expands where it stands**. The inspector fades, the card grows
/// from its 3×4 box into the whole sheet, and the sheet itself takes its taller
/// detent so a pull upward arrives somewhere instead of bouncing back. Nothing
/// closes and nothing else opens: the second sheet was the break in perception.
struct KebabInspector: View {
    let subjectId: String
    var onInspect: (String, String) -> Void
    var onOpenSnapshot: (ChatSnapshot) -> Void
    var onClose: () -> Void

    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @State private var selectedId: String
    @State private var anchor: TalkAnchor?
    @State private var confirmingRemoval = false
    @State private var expanded = false
    @State private var detent: PresentationDetent = Self.restingDetent
    /// Where the miniature sits when the inspector is whole. The growing card
    /// is placed by hand between this rect and the full sheet, so both its
    /// width and its height carry the motion.
    @State private var restingRect: CGRect = .zero

    private static let restingDetent: PresentationDetent = .fraction(0.9)
    private static let space = "kebab"
    /// Room for the sheet's own grab handle above the expanded card.
    private static let expandedTop: CGFloat = 22

    init(
        subjectId: String,
        startingInstanceId: String,
        onInspect: @escaping (String, String) -> Void,
        onOpenSnapshot: @escaping (ChatSnapshot) -> Void,
        onClose: @escaping () -> Void
    ) {
        self.subjectId = subjectId
        self.onInspect = onInspect
        self.onOpenSnapshot = onOpenSnapshot
        self.onClose = onClose
        _selectedId = State(initialValue: startingInstanceId)
    }

    var body: some View {
        GeometryReader { geo in
            ZStack(alignment: .topLeading) {
                resting
                if restingRect.width > 0 {
                    let target = cardRect(in: geo.size)
                    KebabTalkPane(
                        messages: previewMessages,
                        expanded: expanded,
                        onExpand: expand,
                        onCollapse: collapse,
                        onOpenSnapshot: onOpenSnapshot
                    )
                    .frame(width: target.width, height: target.height)
                    .offset(x: target.minX, y: target.minY)
                }
            }
            .coordinateSpace(.named(Self.space))
        }
        .presentationDetents([Self.restingDetent, .large], selection: $detent)
        .presentationDragIndicator(.visible)
        // Dragging the sheet is the same gesture as swiping the chat region:
        // reaching the taller detent opens the talk, dropping back to the
        // resting one puts the miniature back.
        .onChange(of: detent) { _, value in
            let wants = value == .large
            guard wants != expanded else { return }
            if wants { expand() } else { collapse() }
        }
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

    // MARK: - The inspector at rest

    private var instances: [Instance] { store.instances(for: subjectId) }

    private var resting: some View {
        let now = Date()
        let instances = self.instances
        let selected = instances.first { $0.id == selectedId }
        return VStack(alignment: .leading, spacing: 14) {
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
                        widget: { store.widget(instanceId: $0.id) },
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
            }
            // Out of the way before the card is halfway there, so the two are
            // never legible at once.
            .opacity(expanded ? 0 : 1)
            .animation(.easeOut(duration: 0.14), value: expanded)
            .allowsHitTesting(!expanded)
            // The slot the miniature rests in. The card itself is drawn over
            // this, so growing it does not shove the inspector around.
            Color.clear
                .aspectRatio(3.0 / 4.0, contentMode: .fit)
                .onGeometryChange(for: CGRect.self) { proxy in
                    proxy.frame(in: .named(Self.space))
                } action: { rect in
                    guard !expanded, rect.width > 0 else { return }
                    restingRect = rect
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 20)
        .padding(.bottom, 16)
    }

    private func cardRect(in size: CGSize) -> CGRect {
        guard expanded else { return restingRect }
        return CGRect(
            x: 0,
            y: Self.expandedTop,
            width: size.width,
            height: max(0, size.height - Self.expandedTop)
        )
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

    // MARK: - Expanding in place

    /// The thread the miniature was standing on becomes the current one — the
    /// same promotion the old second sheet did, minus the second sheet. The
    /// anchor rides along, so the expanded talk opens on that message and not
    /// at the tail (04-domain-model: the chapter is a scroll target).
    private func expand() {
        let target = anchor ?? talk.anchor(subjectId: subjectId, instanceId: selectedId)
        anchor = target
        talk.promote(threadId: target.threadId, anchorMessageId: target.messageId)
        withAnimation(.snappy) {
            expanded = true
            detent = .large
        }
    }

    private func collapse() {
        withAnimation(.snappy) {
            expanded = false
            detent = Self.restingDetent
        }
    }

    private func add() {
        if let created = store.addInstance(subjectId: subjectId) {
            selectedId = created
        }
    }
}
