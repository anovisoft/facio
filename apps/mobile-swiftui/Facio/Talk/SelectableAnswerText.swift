import SwiftUI
import UIKit

/// The assistant's answer, with one extra item in the selection menu:
/// «что это значит?».
///
/// SwiftUI `Text` can be made selectable but cannot hang an action on the
/// selection, and the selection is the whole point here — it is the strongest
/// signal we will ever get about what needed remembering, because the person
/// pointed at it (05, «Ask about a phrase, keep the answer»). So the bubble is
/// a plain `UITextView`: not editable, not scrolling, no chrome of its own.
struct SelectableAnswerText: UIViewRepresentable {
    let text: String
    var onAsk: (String) -> Void

    func makeUIView(context: Context) -> UITextView {
        let view = UITextView()
        view.delegate = context.coordinator
        view.isEditable = false
        view.isSelectable = true
        // A scrolling text view inside the chat scroll would fight it, and the
        // bubble must size to its own content.
        view.isScrollEnabled = false
        view.backgroundColor = .clear
        view.textContainerInset = .zero
        view.textContainer.lineFragmentPadding = 0
        view.adjustsFontForContentSizeCategory = true
        view.setContentCompressionResistancePriority(.required, for: .vertical)
        view.setContentHuggingPriority(.required, for: .vertical)
        apply(text: text, to: view)
        return view
    }

    func updateUIView(_ view: UITextView, context: Context) {
        context.coordinator.onAsk = onAsk
        apply(text: text, to: view)
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: UITextView, context: Context) -> CGSize? {
        let width = proposal.replacingUnspecifiedDimensions(by: CGSize(width: 320, height: 0)).width
        let fitted = uiView.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude))
        return CGSize(width: width, height: ceil(fitted.height))
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(onAsk: onAsk)
    }

    private func apply(text: String, to view: UITextView) {
        view.font = UIFont.preferredFont(forTextStyle: .body)
        view.textColor = .label
        if view.text != text {
            view.text = text
        }
    }

    @MainActor
    final class Coordinator: NSObject, UITextViewDelegate {
        var onAsk: (String) -> Void

        init(onAsk: @escaping (String) -> Void) {
            self.onAsk = onAsk
        }

        func textView(
            _ textView: UITextView,
            editMenuForTextIn range: NSRange,
            suggestedActions: [UIMenuElement]
        ) -> UIMenu? {
            guard range.length > 0 else { return nil }
            let quote = (textView.text as NSString).substring(with: range)
            let ask = UIAction(title: SelectableAnswerText.askTitle) { [onAsk] _ in
                onAsk(quote)
            }
            // Ours first: copy and lookup stay where they were, this is the one
            // that keeps the answer.
            return UIMenu(children: [ask] + suggestedActions)
        }
    }

    /// The one verb on this gesture. Q31 leaves «remember as a correction» out
    /// on purpose — one gesture, one verb.
    static var askTitle: String {
        String(localized: "что это значит?", comment: "Selection menu item on an assistant answer")
    }

    /// What lands in the thread as the person's own line. The phrase is in the
    /// words as well as in `selection`: the bubble has to read like a question
    /// someone asked, and the mouth reads the same turn either way — the
    /// binding still comes from `selection`, never from these words.
    ///
    /// A drag that swallowed the sentence's full stop would end the line in
    /// «.?». Only the sentence is tidied: `selection.quote` keeps the phrase
    /// exactly as it was selected, because that is what gets stored on the cue.
    static func askUtterance(quote: String) -> String {
        let phrase = quote.trimmingCharacters(in: CharacterSet(charactersIn: " \t\n.,;:!?—–-"))
        return String(localized: "что это значит: \(phrase)?", comment: "Utterance sent when a phrase was selected")
    }
}
