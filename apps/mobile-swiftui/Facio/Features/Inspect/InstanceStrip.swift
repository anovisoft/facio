import SwiftUI

/// The chips over the 7-day calendar: one per case of this practice.
///
/// The caption is the carousel's own (`InstanceFaceLaw.slotCaption`), not a
/// second date formatter. Q34 put several cases on one day, and a strip that
/// only ever says the date turned three of them into three chips reading «8
/// сент.» — the same unreadable row the carousel had before R18 gave it the
/// hour. One rule, two readers.
struct InstanceStrip: View {
    let instances: [Instance]
    @Binding var selectedId: String
    var onAdd: () -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(instances) { instance in
                    let selected = instance.id == selectedId
                    Button {
                        selectedId = instance.id
                    } label: {
                        Text(InstanceFaceLaw.slotCaption(instance, among: instances))
                            .font(.caption.weight(.semibold))
                            .lineLimit(1)
                            .padding(.horizontal, 10)
                            .frame(height: 32)
                    }
                    .buttonStyle(.plain)
                    .foregroundStyle(selected ? Color.primary : Color.secondary)
                    .background(
                        Capsule()
                            .fill(selected ? Color.primary.opacity(0.12) : Color.primary.opacity(0.05))
                    )
                    .accessibilityLabel(InstanceFaceLaw.slotSpokenDate(instance, among: instances))
                    .accessibilityAddTraits(selected ? .isSelected : [])
                }
                Button(action: onAdd) {
                    Image(systemName: "plus")
                        .font(.caption.weight(.semibold))
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
                .foregroundStyle(.primary)
                .background(Capsule().fill(Color.primary.opacity(0.08)))
                .accessibilityLabel("Новый случай")
            }
        }
    }
}
