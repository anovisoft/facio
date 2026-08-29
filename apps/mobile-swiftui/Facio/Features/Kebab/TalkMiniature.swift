import SwiftUI

/// The 3×4 chat miniature of the kebab inspector: a **picture of the talk**,
/// standing on the last snapshot of the instance in the carousel.
///
/// Not a second messenger and not a runtime (never-do #6): nothing in here
/// ticks, sends or scrolls. It is the collapsed half of `KebabTalkPane` — the
/// card, the gestures and the growing all belong to the pane, so the same card
/// stays on screen when the talk opens.
struct TalkMiniature: View {
    let messages: [ChatMessage]
    let placeholder: String

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Разговор")
                .font(.caption.weight(.medium))
                .foregroundStyle(.secondary)
            if messages.isEmpty {
                Text("ещё не начинался")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Spacer(minLength: 0)
            } else {
                Spacer(minLength: 0)
                VStack(alignment: .leading, spacing: 8) {
                    ForEach(messages) { message in
                        MiniBubble(message: message)
                    }
                }
            }
            field
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    /// The input line of the picture. It does not take text — tapping it opens
    /// the real one, in this very card.
    private var field: some View {
        HStack(spacing: 8) {
            Text(placeholder)
                .font(.footnote)
                .foregroundStyle(.secondary)
                .lineLimit(1)
            Spacer(minLength: 0)
            Color.clear
                .frame(width: 28, height: 28)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            Capsule().fill(Color.primary.opacity(0.06))
        )
    }
}

private struct MiniBubble: View {
    let message: ChatMessage

    var body: some View {
        switch message.kind {
        case .user:
            HStack {
                Spacer(minLength: 32)
                text.background(bubble(opacity: 0.10))
            }
        case .assistant:
            HStack {
                text.background(bubble(opacity: 0.06))
                Spacer(minLength: 32)
            }
        case .snapshot:
            if let snapshot = message.snapshot {
                HStack {
                    Spacer(minLength: 12)
                    VStack(alignment: .leading, spacing: 2) {
                        Text(DisplayCopy.title(subjectId: snapshot.subjectId, stored: snapshot.title))
                            .font(.footnote.weight(.semibold))
                            .foregroundStyle(.primary)
                        Text(snapshot.line)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(2)
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(bubble(opacity: 0.08))
                    Spacer(minLength: 12)
                }
            }
        }
    }

    private var text: some View {
        Text(message.text)
            .font(.caption)
            .foregroundStyle(.primary)
            .lineLimit(3)
            .multilineTextAlignment(.leading)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
    }

    private func bubble(opacity: Double) -> some View {
        RoundedRectangle(cornerRadius: 14, style: .continuous)
            .fill(Color.primary.opacity(opacity))
    }
}
