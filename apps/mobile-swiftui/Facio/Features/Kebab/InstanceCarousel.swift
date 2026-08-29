import SwiftUI

/// `[x][ YYY ][z]` from 03-product: past instances on the left, the one you
/// are looking at in the middle, a prepared future one on the right — and `+`
/// instead of `z` when nothing is prepared (the bike).
///
/// Slots are **instances in time**, never schema versions: versions of one
/// object live as snapshots in the chat. Each slot wears **the face of that
/// session** — its own counter number, its own mark, its own hour — with the
/// date and the status as a caption under it, not instead of it.
struct InstanceCarousel: View {
    let instances: [Instance]
    let now: Date
    @Binding var selectedId: String
    /// The widget bound to that very instance, or `nil` when the day kept no
    /// object of its own. Never today's live widget.
    var widget: (Instance) -> Widget?
    var onAdd: () -> Void

    var body: some View {
        ScrollViewReader { proxy in
            // A short row sits centred; a long one scrolls, and `scrollTo`
            // keeps the selected instance in the middle.
            ViewThatFits(in: .horizontal) {
                row
                ScrollView(.horizontal) {
                    row
                }
                .scrollIndicators(.hidden)
                .onAppear {
                    proxy.scrollTo(selectedId, anchor: .center)
                }
                .onChange(of: selectedId) { _, id in
                    withAnimation(.snappy) {
                        proxy.scrollTo(id, anchor: .center)
                    }
                }
            }
        }
    }

    private static let addSlotId = "carousel-add"
    private static let selectedWidth: CGFloat = 92
    private static let restingWidth: CGFloat = 74
    private static let slotHeight: CGFloat = 108

    private var row: some View {
        HStack(alignment: .bottom, spacing: 10) {
            ForEach(instances) { instance in
                slot(instance)
                    .id(instance.id)
            }
            if KebabLaw.showsAddSlot(instances: instances, now: now) {
                addSlot
                    .id(Self.addSlotId)
            }
        }
        .padding(.horizontal, 2)
        .padding(.vertical, 6)
    }

    private func slot(_ instance: Instance) -> some View {
        let selected = instance.id == selectedId
        let face = InstanceFaceLaw.face(instance: instance, widget: widget(instance), now: now)
        let width = selected ? Self.selectedWidth : Self.restingWidth
        return Button {
            selectedId = instance.id
        } label: {
            VStack(spacing: 2) {
                Spacer(minLength: 0)
                InstanceFaceView(
                    face: face,
                    selected: selected,
                    dimmed: instance.status == .completed
                )
                Spacer(minLength: 0)
                Text(DisplayCopy.chipDate(instance.when))
                    .font(selected ? .caption.weight(.semibold) : .caption2.weight(.semibold))
                    .lineLimit(1)
                Text(DisplayCopy.instanceStatus(instance.status))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
            .padding(.horizontal, 6)
            .padding(.vertical, 10)
            .frame(width: width, height: Self.slotHeight)
            .contentShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
        .buttonStyle(.plain)
        .foregroundStyle(selected ? Color.primary : Color.secondary)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color.primary.opacity(selected ? 0.12 : 0.05))
        )
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(DisplayCopy.loudDate(instance.when))
        .accessibilityValue(
            [DisplayCopy.instanceStatus(instance.status), InstanceFaceView.spoken(face)]
                .compactMap { $0 }
                .joined(separator: ", ")
        )
        .accessibilityAddTraits(selected ? [.isButton, .isSelected] : .isButton)
    }

    private var addSlot: some View {
        Button(action: onAdd) {
            Image(systemName: "plus")
                .font(.headline)
                .frame(width: Self.restingWidth, height: Self.slotHeight)
                .contentShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
        .buttonStyle(.plain)
        .foregroundStyle(.primary)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color.primary.opacity(0.08))
        )
        .accessibilityLabel("Новый случай")
    }
}
