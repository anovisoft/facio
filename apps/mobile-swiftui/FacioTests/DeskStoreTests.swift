import XCTest
@testable import Facio

@MainActor
final class DeskStoreTests: XCTestCase {
    func testEditReminderLatestByWritesWindowAndPersists() throws {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-desk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        let store = try DeskStore(repository: repository)

        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy.hour, 19)

        store.editReminderLatestBy(widgetId: "bike-reminder", latestBy: ClockTime(hour: 20, minute: 0))

        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy.hour, 20)
        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy.minute, 0)
        let widget = try XCTUnwrap(store.widget(id: "bike-reminder"))
        XCTAssertEqual(ReminderClock.clock(from: try XCTUnwrap(widget.when)).hour, 20)

        let reloaded = try XCTUnwrap(repository.loadSnapshot())
        XCTAssertEqual(reloaded.subjects.first { $0.id == "bike" }?.window?.latestBy.hour, 20)
    }

    func testEditReminderLatestByWritesEvenWhenDone() throws {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-desk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let store = try DeskStore(repository: DeskRepository(directory: directory))
        store.completeReminder(widgetId: "bike-reminder")
        store.editReminderLatestBy(widgetId: "bike-reminder", latestBy: ClockTime(hour: 18, minute: 30))
        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy, ClockTime(hour: 18, minute: 30))
    }
}
