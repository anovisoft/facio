import XCTest
@testable import Facio

final class CueLawTests: XCTestCase {
    func testCorrectionDefaultsToDoTime() {
        XCTAssertEqual(CueLaw.defaultSurface(for: .correction), .doTime)
        let cue = CueLaw.addCue(id: "c1", subjectId: "push-ups", kind: .correction, text: "brace the core and the glutes")
        XCTAssertEqual(cue.surface, .doTime)
    }

    func testClarificationDefaultsToOnDemand() {
        let cue = CueLaw.addCue(
            id: "c2",
            subjectId: "push-ups",
            kind: .clarification,
            text: "what a hinge is",
            quote: "hinge"
        )
        XCTAssertEqual(cue.surface, .onDemand)
        XCTAssertEqual(cue.quote, "hinge")
    }

    func testTimingCueIsTheSurfaceForReminder() {
        let cue = CueLaw.addCue(
            id: "c3",
            subjectId: "bike",
            kind: .correction,
            text: "зал до 22",
            surface: .timing
        )
        XCTAssertEqual(
            CueLaw.surfaceCue(in: [cue], subjectId: "bike", widgetType: .reminder)?.id,
            "c3"
        )
        XCTAssertNil(CueLaw.doTimeCue(in: [cue], subjectId: "bike"))
    }

    func testAddCueKeepsExplicitSurface() {
        let cue = CueLaw.addCue(
            id: "c3",
            subjectId: "bike",
            kind: .correction,
            text: "зал до 22",
            surface: .timing
        )
        XCTAssertEqual(cue.surface, .timing)
    }

    func testMediaIsAtMostOne() {
        let cue = CueLaw.addCue(
            id: "c4",
            subjectId: "push-ups",
            kind: .clarification,
            text: "the machine",
            media: .link(url: "https://example.com/form")
        )
        XCTAssertEqual(cue.media?.kind, "link")
    }
}
