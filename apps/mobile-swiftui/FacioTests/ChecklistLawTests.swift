import XCTest
@testable import Facio

/// Mirrors `packages/domain/tests/test_catalog_checklist.py`. A divergence
/// between the two is a release hole, not a nit — the lid and the mouth patch
/// the same desk.
final class ChecklistLawTests: XCTestCase {
    private let groceries = ["хлеб", "молоко", "яблоки"]

    private func payload(_ texts: [String]) -> WidgetPayload {
        WidgetPayload(items: texts.enumerated().map { ChecklistItem(id: "item-\($0.offset + 1)", text: $0.element) })
    }

    func testProgressIsCountedAndNeverStored() {
        let base = payload(groceries)
        XCTAssertEqual(ChecklistLaw.progress(of: base).done, 0)
        XCTAssertEqual(ChecklistLaw.progress(of: base).total, 3)

        let ticked = ChecklistLaw.toggle(base, itemId: "item-2")
        XCTAssertEqual(ChecklistLaw.progress(of: ticked).done, 1)
        XCTAssertFalse(ChecklistLaw.isDone(ticked))
        // Pure: the payload handed in is untouched.
        XCTAssertEqual(ChecklistLaw.progress(of: base).done, 0)
    }

    func testTickingTwicePutsTheLineBack() {
        let base = payload(groceries)
        let twice = ChecklistLaw.toggle(ChecklistLaw.toggle(base, itemId: "item-1"), itemId: "item-1")
        XCTAssertEqual(twice, base)
    }

    func testALineThatIsNotThereChangesNothing() {
        let base = payload(groceries)
        XCTAssertEqual(ChecklistLaw.toggle(base, itemId: "item-9"), base)
    }

    func testAnEmptyListIsNotDone() {
        XCTAssertFalse(ChecklistLaw.isDone(WidgetPayload(items: [])))
        XCTAssertFalse(ChecklistLaw.isDone(WidgetPayload()))
        XCTAssertEqual(ChecklistLaw.setDone(WidgetPayload(), true), WidgetPayload())
    }

    func testEveryLineTickedIsDone() {
        let finished = ChecklistLaw.setDone(payload(groceries), true)
        XCTAssertTrue(ChecklistLaw.isDone(finished))
        XCTAssertEqual(ChecklistLaw.progress(of: finished).done, 3)
    }

    /// `done` is optional on the wire (Python defaults it to false); an item
    /// that arrives without it must not fail to decode.
    func testAnItemDecodesWithoutItsDoneFlag() throws {
        let json = Data(#"{"items":[{"id":"item-1","text":"хлеб"}]}"#.utf8)
        let decoded = try FacioJSON.decoder.decode(WidgetPayload.self, from: json)
        XCTAssertEqual(decoded.items?.first?.done, false)
        XCTAssertEqual(decoded.items?.first?.text, "хлеб")
    }

    /// Type owns the shape (never-do #8): the checklist is a 4×2, so the pack
    /// gives it a real slot instead of the default cell.
    func testTheChecklistCarriesItsOwnCellSize() {
        XCTAssertEqual(TileCells.size(for: .wide).width, 4)
        XCTAssertEqual(TileCells.size(for: .wide).height, 2)
        XCTAssertTrue(WidgetType.checklist.showsOnLid)
        // A checklist may be worked on the tile itself (04).
        XCTAssertTrue(WidgetType.checklist.tileRunsLive)
    }

    /// The do-time cue reaches a checklist the same way it reaches a counter —
    /// a bound widget that does not render its subject's cue is broken (04).
    func testTheDoTimeCueReachesAChecklist() {
        let cues = [
            CueLaw.addCue(
                id: "groceries-cue",
                subjectId: "groceries",
                kind: .correction,
                text: "иди после работы, не голодным"
            )
        ]
        let surfaced = CueLaw.surfaceCue(in: cues, subjectId: "groceries", widgetType: .checklist)
        XCTAssertEqual(surfaced?.surface, .doTime)
        XCTAssertEqual(surfaced?.text, "иди после работы, не голодным")
    }
}
