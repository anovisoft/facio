import SwiftUI

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
                        Text(DisplayCopy.chipDate(instance.when))
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
                    .accessibilityLabel(DisplayCopy.loudDate(instance.when))
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
