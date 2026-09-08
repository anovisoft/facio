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
///
/// Expanded it stops being a card at all (R18). R11 kept the pane's own border,
/// corner radius and outer inset all the way to the top, so the finished state
/// read as a sheet standing on a sheet — two edges, two surfaces. The card's
/// chrome now fades out **along the same animation that carries the size**, and
/// the pane lands flush against the sheet: one surface, one top edge, one grab
/// handle.
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
    /// 0 — a card inside the inspector, 1 — the sheet itself. A separate number
    /// from `expanded` on purpose: a `Bool` cannot be interpolated, so a border
    /// and a corner radius read off it would snap at the end of the gesture
    /// instead of going out with the movement.
    @State private var expansion: CGFloat = 0
    @State private var detent: PresentationDetent = Self.restingDetent
    /// Where the miniature sits when the inspector is whole. The growing card
    /// is placed by hand between this rect and the full sheet, so both its
    /// width and its height carry the motion.
    @State private var restingRect: CGRect = .zero
    /// The hour wheels — the same sheet Use opens, never a second picker.
    @State private var hourEdit: ReminderTimeEdit?

    private static let restingDetent: PresentationDetent = .fraction(0.9)
    private static let space = "kebab"
    /// `+` has no case to stand on yet, so it names the sheet instead.
    private static let addHourId = "hour-add"

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
                        expansion: expansion,
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
        .sheet(item: $hourEdit) { edit in
            ReminderTimePickerSheet(edit: edit) { clock in
                saveHour(edit, clock: clock)
            }
        }
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

    /// Occurrences, never the hour a reminder stands on (Q34). A reminder is
    /// not a case of this day, and a queue of days with an alarm wedged in
    /// front of it is the queue reading wrong.
    private var instances: [Instance] { store.occurrenceInstances(for: subjectId) }

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
                    hourRow
                    InstanceCarousel(
                        instances: instances,
                        now: now,
                        selectedId: $selectedId,
                        widget: { store.widget(instanceId: $0.id) },
                        addsHour: store.hourGroup(subjectId: subjectId) != nil,
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
        // Flush against the sheet — no top inset left for the card to show an
        // edge in. The sheet's own grab handle draws over this, which is why
        // the expanded pane starts its header below it (R18).
        return CGRect(x: 0, y: 0, width: size.width, height: size.height)
    }

    // MARK: - The hours of this practice (R18)

    /// The hour of the slot in front of you, when this practice states hours at
    /// all. R17 took the reminder tile off the lid whenever the group already
    /// says every hour, so this is the only place left to correct one.
    private var hourSlot: OccurrenceHourLaw.HourSlot? {
        guard !selectedId.isEmpty else { return nil }
        return store.hourSlot(subjectId: subjectId, instanceId: selectedId)
    }

    @ViewBuilder
    private var hourRow: some View {
        if let slot = hourSlot {
            HStack(spacing: 12) {
                if slot.canMove {
                    Button {
                        hourEdit = ReminderTimeEdit(
                            id: slot.instanceId,
                            window: store.hourGroup(subjectId: subjectId)?.window
                                ?? TimeWindow(latestBy: slot.hour),
                            start: slot.hour
                        )
                    } label: {
                        hourChip(slot.hour, dimmed: false)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(DisplayCopy.hourOfCase(slot.hour))
                    .accessibilityHint("открывает выбор времени")
                } else {
                    // A closed check is history: it keeps its hour and says so,
                    // and there is nothing to press (04 — nothing is rewritten
                    // after the fact).
                    hourChip(slot.hour, dimmed: true)
                        .accessibilityLabel(DisplayCopy.hourOfCase(slot.hour))
                }
                if slot.canDrop {
                    Button {
                        drop(slot)
                    } label: {
                        Text("Убрать час")
                            .font(.subheadline.weight(.medium))
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
                }
            }
        }
    }

    private func hourChip(_ hour: ClockTime, dimmed: Bool) -> some View {
        Text(hour.shortLabel)
            .font(.body.weight(.semibold).monospacedDigit())
            .foregroundStyle(dimmed ? AnyShapeStyle(.secondary) : AnyShapeStyle(.primary))
            .padding(.horizontal, 10)
            .padding(.vertical, 5)
            .background(
                .tertiary.opacity(dimmed ? 0.3 : 0.55),
                in: RoundedRectangle(cornerRadius: 8, style: .continuous)
            )
            .contentShape(Rectangle())
    }

    private func saveHour(_ edit: ReminderTimeEdit, clock: ClockTime) {
        if edit.id == Self.addHourId {
            // The window is idempotent: an hour it already holds comes back as
            // the case already standing on it, and nothing is written twice.
            if let landed = store.addHour(subjectId: subjectId, clock: clock) {
                selectedId = landed
            }
        } else {
            store.moveHour(subjectId: subjectId, instanceId: edit.id, to: clock)
        }
    }

    private func drop(_ slot: OccurrenceHourLaw.HourSlot) {
        if let next = store.dropHour(subjectId: subjectId, instanceId: slot.instanceId) {
            selectedId = next
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

    // MARK: - Expanding in place

    /// The thread the miniature was standing on becomes the current one — the
    /// same promotion the old second sheet did, minus the second sheet. The
    /// anchor rides along, so the expanded talk opens on that message and not
    /// at the tail (04-domain-model: the chapter is a scroll target).
    private func expand() {
        let target = anchor ?? talk.anchor(subjectId: subjectId, instanceId: selectedId)
        anchor = target
        talk.promote(threadId: target.threadId, anchorMessageId: target.messageId)
        // One transaction carries the size, the border and the radius, so the
        // card cannot finish growing while it still looks like a card.
        withAnimation(.snappy) {
            expanded = true
            expansion = 1
            detent = .large
        }
    }

    private func collapse() {
        withAnimation(.snappy) {
            expanded = false
            expansion = 0
            detent = Self.restingDetent
        }
    }

    /// `+`. A practice that states hours is asked which one — the tile in front
    /// of you is not a template for «сейчас» (R18). Everything else clones or
    /// rebinds exactly as before.
    private func add() {
        if let group = store.hourGroup(subjectId: subjectId) {
            hourEdit = ReminderTimeEdit(
                id: Self.addHourId,
                window: group.window,
                start: ReminderClock.nextHour(window: group.window, now: Date())
            )
            return
        }
        if let created = store.addInstance(subjectId: subjectId) {
            selectedId = created
        }
    }
}
