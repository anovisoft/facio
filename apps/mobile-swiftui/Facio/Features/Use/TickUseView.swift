import SwiftUI

struct TickUseView: View {
    let widget: Widget
    let cue: Cue?
    let onToggle: () -> Void

    private var done: Bool { widget.isTickDone }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            if !done, let cue {
                Text(cue.text)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            HStack(spacing: 12) {
                Button(action: onToggle) {
                    Image(systemName: done ? "checkmark.circle.fill" : "circle")
                        .font(.system(size: 44))
                        .foregroundStyle(done ? .primary : .secondary)
                        .frame(width: 44, height: 44)
                        .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel("галочка")
                Text(DisplayCopy.tickState(done: done))
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(.horizontal, FacioPalette.pagePadding)
    }
}
