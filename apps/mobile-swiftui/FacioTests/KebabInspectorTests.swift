import XCTest
@testable import Facio

/// The kebab inspector of 03-product: `postpone` / `delete`, the instance
/// carousel, and the chat miniature standing on the derived chapter.
@MainActor
final class KebabInspectorTests: XCTestCase {
    // MARK: - Chapter is derived, never stored

    func testChapterIsTheLatestSnapshotOfThatInstanceInThatChat() throws {
        let start = try stamp("2026-08-16T09:00:00")
        let thread = makeThread(
            id: "t1",
            messages: [
                .user("цель 30", at: start),
                .snapshot(card(instanceId: "push-ups-open", line: "28 / 30"), at: start.addingTimeInterval(60)),
                .user("и подсказку", at: start.addingTimeInterval(120)),
                .snapshot(card(instanceId: "push-ups-open", line: "28 / 30 · корпус"), at: start.addingTimeInterval(180)),
                .snapshot(card(instanceId: "push-ups-second", line: "0 / 30"), at: start.addingTimeInterval(240)),
            ]
        )

        let latest = TalkAnchorLaw.messageId(in: thread, instanceId: "push-ups-open")

        XCTAssertEqual(latest, thread.messages[3].id, "the chapter is the latest snapshot of that instance")
        XCTAssertEqual(
            TalkAnchorLaw.messageId(in: thread, instanceId: "push-ups-second"),
            thread.messages[4].id
        )
    }

    func testMovingTheCarouselReanchorsInsideTheSameChat() throws {
        let start = try stamp("2026-08-16T09:00:00")
        let thread = makeThread(
            id: "t1",
            messages: [
                .snapshot(card(instanceId: "push-ups-open", line: "28 / 30"), at: start),
                .snapshot(card(instanceId: "push-ups-second", line: "0 / 30"), at: start.addingTimeInterval(60)),
            ]
        )
        let first = TalkAnchorLaw.reanchor(previous: nil, thread: thread, instanceId: "push-ups-open")

        let second = TalkAnchorLaw.reanchor(previous: first, thread: thread, instanceId: "push-ups-second")

        XCTAssertEqual(second.threadId, "t1", "the carousel never opens another chat")
        XCTAssertEqual(second.messageId, thread.messages[1].id)
    }

    /// 07 Q17: an instance with no snapshot here has no chapter.
    func testInstanceWithoutASnapshotLeavesTheMiniatureWhereItStood() throws {
        let start = try stamp("2026-08-16T09:00:00")
        let thread = makeThread(
            id: "t1",
            messages: [.snapshot(card(instanceId: "push-ups-open", line: "28 / 30"), at: start)]
        )
        let standing = TalkAnchorLaw.reanchor(previous: nil, thread: thread, instanceId: "push-ups-open")

        let moved = TalkAnchorLaw.reanchor(previous: standing, thread: thread, instanceId: "push-ups-never-talked")

        XCTAssertEqual(moved, standing, "no snapshot must not move the miniature")
    }

    func testKebabTakesTheChatThatLastBoundTheSubjectElseTheCurrentOne() throws {
        let start = try stamp("2026-08-16T09:00:00")
        let old = makeThread(
            id: "old",
            messages: [.snapshot(card(instanceId: "push-ups-open", line: "25 / 25"), at: start)]
        )
        let newer = makeThread(
            id: "newer",
            messages: [.snapshot(card(instanceId: "push-ups-open", line: "28 / 30"), at: start.addingTimeInterval(3600))]
        )
        let current = makeThread(id: "current", messages: [.user("привет", at: start.addingTimeInterval(7200))])

        XCTAssertEqual(
            TalkAnchorLaw.thread(in: [current, newer, old], current: current, subjectId: "push-ups").id,
            "newer",
            "the chat that last bound this widget wins, even if another was typed in later"
        )
        XCTAssertEqual(
            TalkAnchorLaw.thread(in: [current], current: current, subjectId: "bike").id,
            "current",
            "never bound anywhere → the current chat"
        )
    }

    func testMiniaturePictureEndsOnTheAnchor() throws {
        let start = try stamp("2026-08-16T09:00:00")
        let thread = makeThread(
            id: "t1",
            messages: [
                .user("цель 30", at: start),
                .assistant("тридцать", at: start.addingTimeInterval(30)),
                .snapshot(card(instanceId: "push-ups-open", line: "28 / 30"), at: start.addingTimeInterval(60)),
                .user("а овощи", at: start.addingTimeInterval(120)),
            ]
        )
        let anchor = TalkAnchorLaw.reanchor(previous: nil, thread: thread, instanceId: "push-ups-open")

        let picture = TalkAnchorLaw.preview(in: thread, anchor: anchor, limit: 2)

        XCTAssertEqual(picture.map(\.id), [thread.messages[1].id, thread.messages[2].id])
    }

    // MARK: - Open is Inspect, not Use

    func testOpenLeadsToInspectNotUse() {
        let route = KebabLaw.openRoute(subjectId: "push-ups", instanceId: "push-ups-open")
        XCTAssertEqual(route, .inspect(subjectId: "push-ups", instanceId: "push-ups-open"))
        if case .use = route {
            XCTFail("Open must not open Use — Use cannot swipe between instances")
        }
    }

    // MARK: - Carousel: `z` or `+`

    func testAddSlotOnlyWhenNothingPreparedIsWaiting() throws {
        let now = try stamp("2026-08-16T12:00:00")
        let today = Instance(id: "today", subjectId: "bike", when: now, status: .prepared)
        let past = Instance(
            id: "past",
            subjectId: "bike",
            when: now.addingTimeInterval(-7 * 24 * 3600),
            status: .completed
        )
        let prepared = Instance(
            id: "next",
            subjectId: "bike",
            when: now.addingTimeInterval(2 * 24 * 3600),
            status: .prepared
        )

        XCTAssertTrue(
            KebabLaw.showsAddSlot(instances: [past, today], now: now),
            "today's own instance is the middle slot, not `z`"
        )
        XCTAssertFalse(
            KebabLaw.showsAddSlot(instances: [past, today, prepared], now: now),
            "a prepared future instance is `z`; `+` would duplicate it"
        )
    }

    // MARK: - postpone / delete go through the law

    func testPostponeMovesTheTileToPostponedAndSilencesTheAlarm() throws {
        let now = try stamp("2026-08-16T12:00:00")
        let (store, _) = try makeDesk(now: now)
        store.answerDrift(subjectId: "bike", offer: .moveToToday)
        XCTAssertEqual(store.widget(id: "bike-reminder")?.section, .today)
        XCTAssertFalse(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)

        XCTAssertTrue(store.postpone(subjectId: "bike"))

        let widget = try XCTUnwrap(store.widget(id: "bike-reminder"))
        XCTAssertEqual(widget.section, .postponed)
        XCTAssertEqual(widget.status, .snoozed)
        XCTAssertNotNil(widget.when, "postpone keeps the hour — it is not a skip")
        XCTAssertTrue(store.lid.postponed.contains { $0.id == "bike-reminder" })
        XCTAssertFalse(store.lid.today.contains { item in
            if case .widget(_, let tile) = item { return tile.id == "bike-reminder" }
            return false
        })
        XCTAssertTrue(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
    }

    /// 04: "Nothing is deleted as punishment." «Убрать» archives the widget and
    /// retires the subject — the history stays.
    func testRemoveFromLidKeepsInstancesAndCues() throws {
        let now = try stamp("2026-08-16T12:00:00")
        let (store, repository) = try makeDesk(now: now)
        let instancesBefore = store.snapshot.instances
        let cuesBefore = store.snapshot.cues
        XCTAssertFalse(cuesBefore.filter { $0.subjectId == "push-ups" }.isEmpty)

        XCTAssertTrue(store.removeFromLid(subjectId: "push-ups"))

        XCTAssertEqual(store.snapshot.instances, instancesBefore, "instances are not deleted")
        XCTAssertEqual(store.snapshot.cues, cuesBefore, "cues are not deleted")
        XCTAssertEqual(store.subject(id: "push-ups")?.status, .retired)
        XCTAssertFalse(store.showsOnLid(subjectId: "push-ups"))
        let widget = try XCTUnwrap(store.widget(id: "push-ups-counter"))
        XCTAssertEqual(widget.status, .archived)
        XCTAssertEqual(widget.version, 2, "archive_widget bumps the version, like the law does")
        XCTAssertFalse(store.lid.today.contains { item in
            if case .widget(_, let tile) = item { return tile.subjectId == "push-ups" }
            return false
        })
        let reloaded = try XCTUnwrap(repository.loadSnapshot())
        XCTAssertEqual(reloaded.instances.count, instancesBefore.count)
        XCTAssertEqual(reloaded.cues.count, cuesBefore.count)
    }

    func testRemoveFromLidLeavesTheSubjectOpenableFromDeeds() throws {
        let now = try stamp("2026-08-16T12:00:00")
        let (store, _) = try makeDesk(now: now)
        store.removeFromLid(subjectId: "push-ups")

        XCTAssertNotNil(store.subject(id: "push-ups"), "the practice is retired, not erased")
        XCTAssertFalse(store.instances(for: "push-ups").isEmpty, "the carousel still has its days")
        XCTAssertEqual(store.removeFromLid(subjectId: "push-ups"), false, "already off the lid")
    }

    // MARK: - Holding a tile must not also open Use

    func testLongPressSwallowsTheTapThatFollowsIt() {
        let lock = TapLock()
        XCTAssertTrue(lock.shouldRunTap(), "a plain tap runs")

        lock.consume()

        XCTAssertFalse(lock.shouldRunTap(), "the tap that comes with the long press is swallowed")
        XCTAssertTrue(lock.shouldRunTap(), "the next real tap runs again")
    }

    // MARK: - Helpers

    private func stamp(_ raw: String) throws -> Date {
        try XCTUnwrap(FacioJSON.date(from: raw))
    }

    private func card(instanceId: String, line: String) -> ChatSnapshot {
        ChatSnapshot(
            widgetId: "push-ups-counter",
            subjectId: "push-ups",
            instanceId: instanceId,
            version: 1,
            title: "push-ups",
            line: line
        )
    }

    private func makeThread(id: String, messages: [ChatMessage]) -> ChatThread {
        ChatThread(
            id: id,
            messages: messages,
            createdAt: messages.first?.at ?? Date(),
            updatedAt: messages.last?.at ?? Date()
        )
    }

    private func makeDesk(now: Date) throws -> (DeskStore, DeskRepository) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-kebab-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        try repository.saveSnapshot(SeedFactory.buildSeed(now: now))
        return (try DeskStore(repository: repository, now: { now }), repository)
    }
}
