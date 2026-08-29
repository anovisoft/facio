import Foundation

/// What the client is allowed to draw for the one media item a cue may carry.
///
/// The requirement media answers is **«do not make me leave and search»** (Q33),
/// so the only two outcomes are: render it here, or render nothing. There is no
/// third branch that opens Safari or hands the URL to another app — that would
/// fail the requirement while looking like it satisfied it.
///
/// And nothing here is a precondition. A cue whose media this refuses is a cue
/// with text, which is the whole cue as far as doing the thing is concerned:
/// «a step must be executable without its media» (04), because gyms have bad
/// signal.
enum CueMediaLaw {
    enum Presentation: Equatable {
        /// An embedded page or player, inside the sheet.
        case link(URL)
        /// The person's own picture.
        case photo(URL)
        /// Nothing to draw. Never an error, never a gap in the step.
        case none
    }

    static func presentation(_ media: CueMedia?) -> Presentation {
        switch media {
        case .none:
            return .none
        case .link(let raw):
            return web(raw).map(Presentation.link) ?? .none
        case .photo(let ref):
            // Photos are not stored anywhere yet (upload is not this slice), so
            // the only ref that can be drawn is one that is already an address.
            // A ref pointing at a local store draws nothing rather than a
            // broken frame.
            return web(ref).map(Presentation.photo) ?? .none
        }
    }

    /// Whether the embedded view may follow a navigation.
    ///
    /// `http(s)` stays inside the sheet. Anything else — `youtube://`,
    /// `itms-apps://`, a mail link — is a jump into another app, which is the
    /// exact failure Q33 named, so it is refused rather than handed to the
    /// system.
    static func allowsNavigation(to url: URL?) -> Bool {
        web(url?.absoluteString) != nil
    }

    private static func web(_ raw: String?) -> URL? {
        guard let raw else { return nil }
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, let url = URL(string: trimmed) else { return nil }
        guard let scheme = url.scheme?.lowercased(), scheme == "http" || scheme == "https" else { return nil }
        guard url.host?.isEmpty == false else { return nil }
        return url
    }
}
