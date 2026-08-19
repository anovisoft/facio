import SwiftUI

struct TalksList: View {
    @Environment(TalkStore.self) private var talk
    var onOpen: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Разговоры")
                .font(.headline)
                .foregroundStyle(.primary)
            let threads = talk.listedThreads
            if threads.isEmpty {
                Text("архив пуст")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(threads) { thread in
                    Button {
                        onOpen(thread.id)
                    } label: {
                        VStack(alignment: .leading, spacing: 4) {
                            if thread.id == talk.current.id {
                                Text("сейчас")
                                    .font(.caption.weight(.medium))
                                    .foregroundStyle(.secondary)
                            }
                            Text(preview(thread))
                                .font(.body)
                                .foregroundStyle(.primary)
                                .lineLimit(2)
                                .multilineTextAlignment(.leading)
                            Text(thread.updatedAt, format: .relative(presentation: .named))
                                .font(.caption)
                                .foregroundStyle(.tertiary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel(preview(thread))
                }
            }
        }
    }

    private func preview(_ thread: ChatThread) -> String {
        if let last = thread.messages.last {
            let text = last.text.trimmingCharacters(in: .whitespacesAndNewlines)
            if !text.isEmpty { return text }
        }
        return String(localized: "разговор", comment: "Talks row fallback")
    }
}
