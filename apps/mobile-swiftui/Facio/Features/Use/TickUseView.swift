import SwiftUI

struct TickUseView: View {
    let widget: Widget
    let lookOnly: Bool
    let onToggle: () -> Void

    private var done: Bool { widget.payload.done == true || lookOnly }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(spacing: 14) {
                Button(action: onToggle) {
                    Image(systemName: done ? "checkmark" : "")
                        .font(.title2.weight(.bold))
                        .foregroundStyle(.primary)
                        .frame(width: 56, height: 56)
                        .facioCircleGlass(interactive: true)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("галочка")
                Text(done ? "готово" : "на Сегодня")
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, FacioPalette.pagePadding)
    }
}
