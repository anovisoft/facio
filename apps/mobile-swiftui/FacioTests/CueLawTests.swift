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

// MARK: - The tick renders what the law hands it

/// 04: "A widget bound to a subject renders that subject's do-time cues.
/// Cues that exist and are not shown mean the widget is broken (P9)."
///
/// CueLaw always answered `.tick` with a do-time cue; the tile had no field to
/// put it in and the cell passed none, so a conclusion left on vegetables was
/// invisible on the lid and on Use, and its hits never counted. These pin the
/// wiring, since a view that silently drops a value cannot fail a law test.
extension CueLawTests {
    func testTickAsksTheLawForADoTimeCue() throws {
        let cue = CueLaw.addCue(
            id: "veg-cue",
            subjectId: "vegetables",
            kind: .correction,
            text: "овощ в каждый приём",
            surface: .doTime
        )
        let surfaced = CueLaw.surfaceCue(in: [cue], subjectId: "vegetables", widgetType: .tick)
        XCTAssertEqual(surfaced?.id, "veg-cue")
    }

    func testTickTileTakesTheCueTheLawHandsIt() throws {
        let cue = CueLaw.addCue(
            id: "veg-cue",
            subjectId: "vegetables",
            kind: .correction,
            text: "овощ в каждый приём",
            surface: .doTime
        )
        let widget = Widget(
            id: "vegetables-tick",
            type: .tick,
            title: "vegetables",
            payload: WidgetPayload(),
            status: .ready,
            when: nil,
            section: .today,
            groupId: nil,
            subjectId: "vegetables",
            instanceId: "vegetables-open",
            tileSize: .compact,
            version: 1
        )
        // The initialiser is the contract this restores: the tile had no cue
        // parameter at all, so this line did not compile and the conclusion a
        // conversation left on vegetables was invisible at do-time.
        let tile = TickTile(
            widget: widget,
            cue: cue,
            onOpen: nil,
            onToggle: nil,
            onKebab: {},
            onSurfaced: {}
        )
        XCTAssertEqual(tile.cue?.text, "овощ в каждый приём")
        XCTAssertEqual(tile.widget.subjectId, cue.subjectId)
    }
}
