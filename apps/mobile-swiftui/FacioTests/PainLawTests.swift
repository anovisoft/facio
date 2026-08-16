import XCTest
@testable import Facio

final class PainLawTests: XCTestCase {
    func testLowerBackTakingLoadIsPain() {
        XCTAssertTrue(PainLaw.reportsPain("поясница забирает нагрузку"))
    }

    func testHurtsAndInjuryArePain() {
        XCTAssertTrue(PainLaw.reportsPain("больно, давай 40"))
        XCTAssertTrue(PainLaw.reportsPain("it hurts"))
        XCTAssertTrue(PainLaw.reportsPain("травма в плече"))
    }

    func testPlainTargetIsNotPain() {
        XCTAssertFalse(PainLaw.reportsPain("цель 30"))
        XCTAssertFalse(PainLaw.reportsPain("давай три раза в неделю"))
    }
}
