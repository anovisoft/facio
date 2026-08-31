import SwiftUI
import WebKit

/// The one media item a cue may carry, drawn where the cue is (04, Q33).
///
/// Three rules hold this view down:
///
/// * **In place.** A `link` is a player inside the sheet, not a jump into
///   Safari — the requirement is «do not make me leave and search», and an
///   external app fails it while looking like a feature.
/// * **Never a precondition.** It loads beside the text, never in front of it.
///   No network, dead link, slow gym Wi-Fi: the explanation is already on
///   screen and stays there, and this box quietly says it could not open.
/// * **No autoplay.** A preview is allowed, a player that starts on its own is
///   not. `mediaTypesRequiringUserActionForPlayback = .all` is where that lives.
struct CueMediaView: View {
    let media: CueMedia?

    var body: some View {
        switch CueMediaLaw.presentation(media) {
        case .none:
            EmptyView()
        case .link(let url):
            EmbeddedLink(url: url)
        case .photo(let url):
            EmbeddedPhoto(url: url)
        }
    }
}

private let mediaAspect: CGFloat = 16 / 9
private let mediaRadius: CGFloat = 16

/// The quiet line a box shows when it could not load. Deliberately small and
/// grey: nothing here is broken, the step still runs.
private struct MediaUnavailable: View {
    var body: some View {
        Text("медиа не открылось")
            .font(.footnote)
            .foregroundStyle(.secondary)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct EmbeddedPhoto: View {
    let url: URL

    var body: some View {
        AsyncImage(url: url) { phase in
            switch phase {
            case .success(let image):
                image
                    .resizable()
                    .scaledToFit()
                    .accessibilityLabel(Text("фото"))
            case .failure:
                MediaUnavailable()
            default:
                ProgressView()
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: mediaRadius, style: .continuous))
    }
}

private struct EmbeddedLink: View {
    let url: URL
    @State private var failed = false

    var body: some View {
        Group {
            if failed {
                MediaUnavailable()
            } else {
                InlineWebView(url: url, failed: $failed)
                    .aspectRatio(mediaAspect, contentMode: .fit)
                    .clipShape(RoundedRectangle(cornerRadius: mediaRadius, style: .continuous))
                    .accessibilityLabel(Text("видео"))
            }
        }
    }
}

/// `WKWebView` with the two settings that make it a step's player rather than a
/// browser: playback stays inline, and nothing starts without a finger.
private struct InlineWebView: UIViewRepresentable {
    let url: URL
    @Binding var failed: Bool

    func makeCoordinator() -> Coordinator { Coordinator(failed: $failed) }

    func makeUIView(context: Context) -> WKWebView {
        let configuration = WKWebViewConfiguration()
        configuration.allowsInlineMediaPlayback = true
        // 04: «A thumbnail inline is allowed; an autoplaying player is not.»
        configuration.mediaTypesRequiringUserActionForPlayback = .all
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.isOpaque = false
        view.backgroundColor = .clear
        view.scrollView.backgroundColor = .clear
        // The sheet scrolls; the embed should not fight it.
        view.scrollView.isScrollEnabled = false
        view.load(URLRequest(url: url))
        return view
    }

    func updateUIView(_ view: WKWebView, context: Context) {
        guard view.url != url, !view.isLoading else { return }
        view.load(URLRequest(url: url))
    }

    @MainActor
    final class Coordinator: NSObject, WKNavigationDelegate {
        private let failed: Binding<Bool>

        init(failed: Binding<Bool>) {
            self.failed = failed
        }

        func webView(
            _ webView: WKWebView,
            decidePolicyFor navigationAction: WKNavigationAction,
            decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
        ) {
            // Everything that is not the web stays refused: a `youtube://` or an
            // App Store link would take the person out of the step, which is the
            // requirement media exists to satisfy (Q33).
            decisionHandler(CueMediaLaw.allowsNavigation(to: navigationAction.request.url) ? .allow : .cancel)
        }

        func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
            failed.wrappedValue = true
        }

        func webView(
            _ webView: WKWebView,
            didFailProvisionalNavigation navigation: WKNavigation!,
            withError error: Error
        ) {
            failed.wrappedValue = true
        }
    }
}
