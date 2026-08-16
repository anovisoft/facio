import XCTest
@testable import Facio

final class SeedFactoryTests: XCTestCase {
    func testSeedPutsFoundingSubjectsOnToday() throws {
        let now = try DomainFixtures.now()
        let seed = try SeedFactory.buildSeed(now: now)
        XCTAssertEqual(seed.widgets.map(\.section), [.today, .today])
        XCTAssertEqual(Set(seed.widgets.map(\.id)), ["push-ups-counter", "vegetables-tick"])
        let cue = try XCTUnwrap(CueLaw.doTimeCue(in: seed.cues, subjectId: "push-ups"))
        XCTAssertEqual(cue.text, "держи корпус и ягодицы")
        XCTAssertEqual(cue.surface, .doTime)
    }
}
