import XCTest
@testable import Facio

/// Day zero (03-product, «Composer») and the counter that never got a goal.
/// Both are about not showing a person a number he never named.
@MainActor
final class DayZeroTests: XCTestCase {

    // MARK: - Chips

    func testChipsStandOnAnEmptyDesk() throws {
        let (store, _) = try makeStore(seeded: false)
        XCTAssertTrue(store.showsDayZeroChips)
        XCTAssertEqual(DayZeroChip.allCases, [.today, .dinner, .gym])
    }

    func testChipsAreGoneOnADeskWithPractices() throws {
        let (store, _) = try makeStore(seeded: true)
        XCTAssertFalse(store.showsDayZeroChips)
    }

    /// The lock from never-do #15 read from the other side: an ordinary empty
    /// Сегодня is a rest day, not day zero. Once a subject has existed the
    /// chips never blink again, even when the desk is handed back empty.
    func testChipsNeverComeBackOnceASubjectExisted() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeStore(seeded: false, now: now)
        XCTAssertTrue(store.showsDayZeroChips)

        store.applyTalk(try SeedFactory.buildSeed(now: now))
        XCTAssertFalse(store.showsDayZeroChips)

        store.applyTalk(DeskSnapshot(subjects: [], cues: [], instances: [], widgets: []))
        XCTAssertTrue(store.snapshot.subjects.isEmpty)
        XCTAssertFalse(store.showsDayZeroChips)

        let relaunched = try DeskStore(repository: repository, now: { now })
        XCTAssertFalse(relaunched.showsDayZeroChips)
    }

    /// A desk that already carried practices before this build shipped must not
    /// be greeted as a first launch.
    func testLatchClosesOnLaunchOfAnAlreadySeededDesk() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeStore(seeded: true, now: now)
        XCTAssertTrue(store.dayZeroClosed)
        XCTAssertTrue(repository.dayZeroClosed())
    }

    func testChipTapPutsItsTextInTheMouthField() throws {
        let talk = try makeTalk()
        XCTAssertFalse(talk.sheetOpen)

        talk.startDraft(DayZeroChip.gym.text)

        XCTAssertEqual(talk.draft, DayZeroChip.gym.text)
        XCTAssertTrue(talk.sheetOpen)
        // The chip opens the sheet; the person decides whether to send.
        XCTAssertTrue(talk.current.messages.isEmpty)
    }

    func testChipsCarryTheThreeWaysIn() {
        XCTAssertEqual(Set(DayZeroChip.allCases.map(\.text)).count, 3)
        for chip in DayZeroChip.allCases {
            XCTAssertFalse(chip.text.trimmingCharacters(in: .whitespaces).isEmpty)
        }
    }

    // MARK: - A counter with no goal

    func testCounterFaceDrawsTheGoalOnlyWhenThereIsOne() {
        XCTAssertTrue(DisplayCopy.counterFace(count: 29, goal: 30).contains(" / "))
        XCTAssertFalse(DisplayCopy.counterFace(count: 12, goal: nil).contains(" / "))
        XCTAssertFalse(DisplayCopy.counterFace(count: 12, goal: nil).contains("0"))
    }

    func testCounterWithoutAGoalReadsAsJustTheNumber() {
        let label = DisplayCopy.counterAccessibility(title: "Зал", count: 12, goal: nil, cue: nil)
        XCTAssertFalse(label.contains(" / "))
        XCTAssertFalse(label.contains("0"))
        XCTAssertTrue(label.contains("12"))

        let withCue = DisplayCopy.counterAccessibility(title: "Зал", count: 12, goal: nil, cue: "не спеши")
        XCTAssertFalse(withCue.contains(" / "))
        XCTAssertTrue(withCue.contains("не спеши"))
    }

    func testCounterWithAGoalStillReadsIt() {
        let label = DisplayCopy.counterAccessibility(title: "Отжимания", count: 29, goal: 30, cue: nil)
        XCTAssertTrue(label.contains("30"))
        XCTAssertTrue(label.contains("29"))

        let withCue = DisplayCopy.counterAccessibility(title: "Отжимания", count: 29, goal: 30, cue: "держи корпус")
        XCTAssertTrue(withCue.contains("30"))
        XCTAssertTrue(withCue.contains("держи корпус"))
    }

    func testZeroTargetIsNotAGoal() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let widget = Widget(
            id: "gym-counter",
            type: .counter,
            title: "зал",
            payload: WidgetPayload(count: 12, target: 0),
            status: .running,
            when: now,
            section: .today,
            subjectId: "gym",
            instanceId: "gym-open"
        )
        XCTAssertNil(widget.counterGoal)
        XCTAssertEqual(widget.counterCount, 12)

        var named = widget
        named.payload.target = 30
        XCTAssertEqual(named.counterGoal, 30)
    }

    // MARK: - Helpers

    private func makeStore(
        seeded: Bool,
        now: Date = Date()
    ) throws -> (DeskStore, DeskRepository) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-day-zero-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        if seeded {
            try repository.saveSnapshot(SeedFactory.buildSeed(now: now))
        }
        return (try DeskStore(repository: repository, now: { now }), repository)
    }

    private func makeTalk() throws -> TalkStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-day-zero-talk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return try TalkStore(
            repository: TalkRepository(directory: directory),
            client: .stub { _ in throw TalkClientError.transport }
        )
    }
}
