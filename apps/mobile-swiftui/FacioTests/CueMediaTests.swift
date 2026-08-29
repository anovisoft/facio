import XCTest
@testable import Facio

/// R14 part B. What the `?` sheet is allowed to draw for the one media item a
/// cue may carry — and, just as load-bearing, what it refuses to draw.
final class CueMediaTests: XCTestCase {
    func testALinkIsDrawnInPlace() throws {
        XCTAssertEqual(
            CueMediaLaw.presentation(.link(url: "https://youtu.be/abc123")),
            .link(URL(string: "https://youtu.be/abc123")!)
        )
    }

    func testAPhotoRefThatIsAnAddressIsDrawn() throws {
        XCTAssertEqual(
            CueMediaLaw.presentation(.photo(ref: "https://example.com/machine.jpg")),
            .photo(URL(string: "https://example.com/machine.jpg")!)
        )
    }

    func testAPhotoRefWithNowhereToLoadFromDrawsNothing() throws {
        // There is no file store yet. A ref into one is not an error and not a
        // broken frame — it is a cue with text, which is a whole cue.
        XCTAssertEqual(CueMediaLaw.presentation(.photo(ref: "local/machine-1")), .none)
    }

    func testACueWithNoMediaIsStillAWholeCue() throws {
        XCTAssertEqual(CueMediaLaw.presentation(nil), .none)
    }

    func testASchemeThatWouldLeaveTheAppIsRefused() throws {
        // Q33: the requirement media answers is «do not make me leave and
        // search». Handing the URL to another app fails it while looking like a
        // feature, so these draw nothing rather than jump out.
        for raw in ["youtube://watch?v=abc", "itms-apps://apple.com", "file:///etc/passwd", "javascript:alert(1)"] {
            XCTAssertEqual(CueMediaLaw.presentation(.link(url: raw)), .none, raw)
            XCTAssertFalse(CueMediaLaw.allowsNavigation(to: URL(string: raw)), raw)
        }
    }

    func testGarbageInTheUrlDrawsNothing() throws {
        XCTAssertEqual(CueMediaLaw.presentation(.link(url: "   ")), .none)
        XCTAssertEqual(CueMediaLaw.presentation(.link(url: "not a url at all")), .none)
        XCTAssertEqual(CueMediaLaw.presentation(.link(url: "https://")), .none)
    }

    func testTheEmbeddedViewOnlyFollowsTheWeb() throws {
        XCTAssertTrue(CueMediaLaw.allowsNavigation(to: URL(string: "https://www.youtube.com/embed/abc")))
        XCTAssertTrue(CueMediaLaw.allowsNavigation(to: URL(string: "http://192.168.1.17/clip.mp4")))
        XCTAssertFalse(CueMediaLaw.allowsNavigation(to: nil))
    }

    /// Media rides its cue's surface (04): a `clarification` sits behind the
    /// `?`, and do-time stays text. The sheet reads the on-demand cues and
    /// nothing else, so a `correction` with media never reaches rep one.
    func testMediaRidesTheSurfaceItsCueHas() throws {
        let cues = [
            Cue(
                id: "c-do",
                subjectId: "push-ups",
                kind: .correction,
                text: "держи корпус",
                media: .link(url: "https://example.com/form.mp4"),
                surface: .doTime
            ),
            Cue(
                id: "c-help",
                subjectId: "push-ups",
                kind: .clarification,
                text: "таз не роняем",
                media: .link(url: "https://example.com/hips.mp4"),
                surface: .onDemand
            ),
        ]
        let behindTheQuestionMark = ClarificationLaw.onDemandCues(in: cues, subjectId: "push-ups")
        XCTAssertEqual(behindTheQuestionMark.map(\.id), ["c-help"])
    }
}
