import SwiftUI

struct TickUseView: View {
    let widget: Widget
    let lookOnly: Bool
    let onToggle: () -> Void

    private var done: Bool { widget.payload.done == true || lookOnly }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(spacing: 12) {
                Button(action: onToggle) {
                    Image(systemName: done ? "checkmark.circle.fill" : "circle")
                        .font(.title2)
                        .foregroundStyle(done ? .primary : .secondary)
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
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
