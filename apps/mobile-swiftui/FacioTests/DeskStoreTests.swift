import XCTest
@testable import Facio

@MainActor
final class DeskStoreTests: XCTestCase {
    func testEditReminderLatestByWritesWindowAndPersists() throws {
        let (store, repository) = try makeDesk()
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
        let (store, _) = try makeDesk()
        store.completeReminder(widgetId: "bike-reminder")
        store.editReminderLatestBy(widgetId: "bike-reminder", latestBy: ClockTime(hour: 18, minute: 30))
        XCTAssertEqual(store.windowFor(subjectId: "bike")?.latestBy, ClockTime(hour: 18, minute: 30))
    }

    func testTickCounterWritesWidgetAndInstanceTogether() throws {
        let (store, _) = try makeDesk()
        store.tickCounter(widgetId: "push-ups-counter", delta: 1)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 29)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .running)
        XCTAssertEqual(store.snapshot.instances.first { $0.id == "push-ups-open" }?.status, .inProgress)
    }

    func testMarkCueSurfacedOncePerPlacePerDay() throws {
        let (store, _) = try makeDesk()
        let before = store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced ?? 0
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, before + 1)
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "use")
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, before + 2)
    }

    func testMarkCueSurfacedSurvivesRelaunch() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeDesk(now: now)
        store.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        let afterFirst = store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced
        let reloaded = try DeskStore(repository: repository, now: { now })
        reloaded.markCueSurfaced(widgetId: "push-ups-counter", place: "tile")
        XCTAssertEqual(reloaded.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, afterFirst)
    }

    func testAnswerDriftMoveToToday() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        XCTAssertEqual(store.lid.driftCard?.subjectId, "bike")
        XCTAssertTrue(store.surfaces(try XCTUnwrap(store.lid.driftCard)))
        XCTAssertEqual(store.widget(id: "bike-reminder")?.section, .lifetime)

        store.answerDrift(subjectId: "bike", offer: .moveToToday)

        XCTAssertEqual(store.widget(id: "bike-reminder")?.section, .today)
        XCTAssertEqual(store.snapshot.driftAsks["bike"]?.asksMade, 1)
        XCTAssertFalse(store.surfaces(try XCTUnwrap(store.lid.driftCard)))
        let fireHour = Calendar.current.component(.hour, from: try XCTUnwrap(store.widget(id: "bike-reminder")?.when))
        XCTAssertEqual(fireHour, 19)
    }

    func testAnswerDriftOnceAWeekShrinksCadence() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeDesk(now: now)
        store.answerDrift(subjectId: "bike", offer: .onceAWeek)
        let bike = try XCTUnwrap(store.subject(id: "bike"))
        XCTAssertEqual(bike.status, .shrunk)
        XCTAssertEqual(bike.cadence.count, 1)
        XCTAssertEqual(bike.cadence.period, .week)
        XCTAssertFalse(store.surfaces(try XCTUnwrap(store.lid.driftCard)))
        let reloaded = try XCTUnwrap(repository.loadSnapshot())
        XCTAssertEqual(reloaded.subjects.first { $0.id == "bike" }?.cadence.count, 1)
        XCTAssertEqual(reloaded.subjects.first { $0.id == "bike" }?.status, .shrunk)
    }

    func testAnswerDriftRetireHidesSubjectAndAlarm() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        XCTAssertFalse(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
        store.answerDrift(subjectId: "bike", offer: .retire)
        XCTAssertEqual(store.subject(id: "bike")?.status, .retired)
        XCTAssertFalse(store.showsOnLid(subjectId: "bike"))
        XCTAssertNil(store.lid.driftCard)
        XCTAssertTrue(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
    }

    func testAnswerDriftDoesNotRaiseCadence() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        XCTAssertEqual(store.subject(id: "bike")?.cadence.count, 2)
        store.answerDrift(subjectId: "bike", offer: .onceAWeek)
        XCTAssertEqual(store.subject(id: "bike")?.cadence.count, 1)
    }

    func testOldDeskJsonWithoutDriftAsksDecodes() throws {
        let json = """
        {"cues":[],"instances":[],"subjects":[],"widgets":[]}
        """.data(using: .utf8)!
        let snapshot = try FacioJSON.decoder.decode(DeskSnapshot.self, from: json)
        XCTAssertEqual(snapshot.driftAsks, [:])
        XCTAssertEqual(snapshot.driftAskedAt, [:])
    }

    func testCompleteReminderDropsAlarm() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        XCTAssertFalse(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
        store.completeReminder(widgetId: "bike-reminder")
        XCTAssertTrue(ReminderScheduler.alarms(from: store.snapshot, now: now).isEmpty)
    }

    func testAddInstanceRebindsLifetimeReminderToToday() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        XCTAssertEqual(store.widget(id: "bike-reminder")?.section, .lifetime)
        let before = store.instances(for: "bike").count

        let created = try XCTUnwrap(store.addInstance(subjectId: "bike"))

        XCTAssertEqual(store.instances(for: "bike").count, before + 1)
        let widget = try XCTUnwrap(store.widget(id: "bike-reminder"))
        XCTAssertEqual(widget.instanceId, created)
        XCTAssertEqual(widget.section, .today)
        XCTAssertEqual(widget.status, .ready)
        XCTAssertNil(store.widget(id: "w-\(created)"))
    }

    func testAddInstanceClonesWhenTodayReady() throws {
        let (store, _) = try makeDesk()
        let created = try XCTUnwrap(store.addInstance(subjectId: "push-ups"))
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.instanceId, "push-ups-open")
        let clone = try XCTUnwrap(store.widget(id: "w-\(created)"))
        XCTAssertEqual(clone.section, .today)
        XCTAssertEqual(clone.counterCount, 0)
        XCTAssertEqual(clone.counterTarget, 30)
        XCTAssertEqual(clone.status, .ready)
    }

    func testAddInstanceKeepsDoneTodayAndAddsFreshTile() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        store.completeCounter(widgetId: "push-ups-counter")
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .done)

        let created = try XCTUnwrap(store.addInstance(subjectId: "push-ups"))

        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .done)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.instanceId, "push-ups-open")
        let clone = try XCTUnwrap(store.widget(id: "w-\(created)"))
        XCTAssertEqual(clone.status, .ready)
        XCTAssertEqual(clone.section, .today)
    }

    func testApplyTalkWritesCueAndKeepsTile() throws {
        let (store, repository) = try makeDesk()
        var desk = store.snapshot
        let cue = CueLaw.addCue(
            id: "push-ups-brace-talk",
            subjectId: "push-ups",
            kind: .correction,
            text: "держи корпус и ягодицы",
            surface: .doTime,
            origin: CueOrigin(chatId: "golden", messageId: nil)
        )
        desk.cues.append(cue)
        if let index = desk.subjects.firstIndex(where: { $0.id == "push-ups" }) {
            desk.subjects[index].cueIds.append(cue.id)
        }

        store.applyTalk(desk)

        XCTAssertEqual(store.cueFor(subjectId: "push-ups")?.id, "push-ups-brace-talk")
        XCTAssertEqual(store.cueFor(subjectId: "push-ups")?.text, "держи корпус и ягодицы")
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 28)
        let reloaded = try XCTUnwrap(repository.loadSnapshot())
        XCTAssertEqual(reloaded.cues.last?.id, "push-ups-brace-talk")
    }

    func testApplyTalkKeepsRunningCountWhenTalkAddsCue() throws {
        let (store, _) = try makeDesk()
        store.tickCounter(widgetId: "push-ups-counter", delta: 1)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 29)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .running)

        var incoming = store.snapshot
        if let index = incoming.widgets.firstIndex(where: { $0.id == "push-ups-counter" }) {
            incoming.widgets[index].payload.count = 28
            incoming.widgets[index].status = .ready
        }
        let cue = CueLaw.addCue(
            id: "push-ups-brace-talk",
            subjectId: "push-ups",
            kind: .correction,
            text: "четыре чистых, корпус как доска",
            surface: .doTime,
            origin: CueOrigin(chatId: "golden", messageId: nil)
        )
        incoming.cues.append(cue)
        if let index = incoming.subjects.firstIndex(where: { $0.id == "push-ups" }) {
            incoming.subjects[index].cueIds.append(cue.id)
        }

        store.applyTalk(
            incoming,
            toolCalls: [
                TalkToolCall(
                    name: "add_cue",
                    arguments: [
                        "id": .string("push-ups-brace-talk"),
                        "subject_id": .string("push-ups"),
                    ],
                    ok: true
                ),
            ]
        )

        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 29)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .running)
        XCTAssertEqual(store.cueFor(subjectId: "push-ups")?.id, "push-ups-brace-talk")
        XCTAssertEqual(store.cueFor(subjectId: "push-ups")?.text, "четыре чистых, корпус как доска")
    }

    func testApplyTalkAppliesIncomingCountWhenUpdateWidgetSucceeds() throws {
        let (store, _) = try makeDesk()
        store.tickCounter(widgetId: "push-ups-counter", delta: 1)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 29)
        XCTAssertEqual(store.widget(id: "push-ups-counter")?.status, .running)

        var incoming = store.snapshot
        if let index = incoming.widgets.firstIndex(where: { $0.id == "push-ups-counter" }) {
            incoming.widgets[index].payload.count = 4
            incoming.widgets[index].payload.target = 30
        }

        store.applyTalk(
            incoming,
            toolCalls: [
                TalkToolCall(
                    name: "update_widget",
                    arguments: [
                        "widget_id": .string("push-ups-counter"),
                        "target": .int(30),
                        "count": .int(4),
                    ],
                    ok: true
                ),
            ]
        )

        XCTAssertEqual(store.widget(id: "push-ups-counter")?.counterCount, 4)
    }

    func testApplyTalkGymCounterHasNoReminder() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        var incoming = store.snapshot
        incoming.subjects.append(
            Subject(
                id: "gym",
                title: "зал",
                cadence: try Cadence.of(count: 3, period: .week),
                instanceIds: ["gym-open"]
            )
        )
        incoming.instances.append(Instance(id: "gym-open", subjectId: "gym", when: now, status: .prepared))
        incoming.widgets.append(
            Widget(
                id: "gym-counter",
                type: .counter,
                title: "зал",
                payload: WidgetPayload(count: 0, target: 0),
                status: .ready,
                section: .today,
                subjectId: "gym",
                instanceId: "gym-open",
                tileSize: .compact
            )
        )

        store.applyTalk(
            incoming,
            toolCalls: [
                TalkToolCall(
                    name: "create_widget",
                    arguments: [
                        "type": .string("counter"),
                        "title": .string("зал"),
                        "subject_id": .string("gym"),
                    ],
                    ok: true
                ),
            ]
        )

        XCTAssertEqual(store.snapshot.widgets.filter { $0.subjectId == "gym" && $0.type == .reminder }.count, 0)
        XCTAssertNotNil(store.widget(id: "gym-counter"))
        XCTAssertNotNil(store.widget(id: "bike-reminder"))
    }

    func testApplyTalkAddsReminderTileWide() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        var incoming = store.snapshot
        incoming.widgets.append(
            Widget(
                id: "vegetables-reminder",
                type: .reminder,
                title: "vegetables",
                payload: WidgetPayload(fireAt: now),
                status: .ready,
                when: now,
                section: .today,
                subjectId: "vegetables",
                instanceId: "vegetables-open",
                tileSize: .wide
            )
        )

        store.applyTalk(incoming)

        let reminder = try XCTUnwrap(
            store.snapshot.widgets.first { $0.subjectId == "vegetables" && $0.type == .reminder }
        )
        XCTAssertEqual(reminder.type, .reminder)
        XCTAssertEqual(reminder.tileSize, .wide)
    }

    private func makeDesk(now: Date = Date()) throws -> (DeskStore, DeskRepository) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-desk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        return (try DeskStore(repository: repository, now: { now }), repository)
    }
}
