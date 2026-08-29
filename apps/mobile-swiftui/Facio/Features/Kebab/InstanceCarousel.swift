import SwiftUI

/// `[x][ YYY ][z]` from 03-product: past instances on the left, the one you
/// are looking at in the middle, a prepared future one on the right — and `+`
/// instead of `z` when nothing is prepared (the bike).
///
/// Slots are **instances in time**, never schema versions: versions of one
/// object live as snapshots in the chat.
struct InstanceCarousel: View {
    let instances: [Instance]
    let now: Date
    @Binding var selectedId: String
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

    private var row: some View {
        HStack(spacing: 10) {
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
        let side: CGFloat = selected ? 92 : 72
        return Button {
            selectedId = instance.id
        } label: {
            VStack(spacing: 4) {
                Text(DisplayCopy.chipDate(instance.when))
                    .font(selected ? .subheadline.weight(.semibold) : .caption.weight(.semibold))
                    .lineLimit(1)
                Text(DisplayCopy.instanceStatus(instance.status))
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
            }
            .padding(.horizontal, 6)
            .frame(width: side, height: side)
            .contentShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
        .buttonStyle(.plain)
        .foregroundStyle(selected ? Color.primary : Color.secondary)
        .background(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .fill(Color.primary.opacity(selected ? 0.12 : 0.05))
        )
        .accessibilityLabel(DisplayCopy.loudDate(instance.when))
        .accessibilityValue(DisplayCopy.instanceStatus(instance.status))
        .accessibilityAddTraits(selected ? .isSelected : [])
    }

    private var addSlot: some View {
        Button(action: onAdd) {
            Image(systemName: "plus")
                .font(.headline)
                .frame(width: 72, height: 72)
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
