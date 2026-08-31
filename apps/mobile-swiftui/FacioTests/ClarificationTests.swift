import XCTest
@testable import Facio

/// «Ask about a phrase, keep the answer» (05) on the client side: the selection
/// that leaves, the `?` that brings it back, and the one check that asks
/// whether it landed (Q32).
@MainActor
final class ClarificationTests: XCTestCase {
    // MARK: - An explanation is looked up, never shown at rep one

    func testOnDemandCueIsNeverTheInlineCue() throws {
        let (store, _) = try makeDesk(clarification: true)
        let counter = try XCTUnwrap(store.widget(id: "push-ups-counter"))

        // Inline at do-time stays the correction, and only the correction.
        XCTAssertEqual(store.cueFor(subjectId: "push-ups")?.id, "push-ups-brace")
        XCTAssertEqual(store.surfaceCue(for: counter)?.id, "push-ups-brace")
        XCTAssertEqual(store.surfaceCue(for: counter)?.surface, .doTime)

        // The clarification is only reachable behind the `?`.
        XCTAssertEqual(store.explanations(for: counter).map(\.id), ["push-ups-chest"])
    }

    func testAPracticeWhoseOnlyCueIsAnExplanationDrawsNothingInline() throws {
        let (store, _) = try makeDesk(clarification: true, correction: false)
        let counter = try XCTUnwrap(store.widget(id: "push-ups-counter"))
        XCTAssertNil(store.cueFor(subjectId: "push-ups"))
        XCTAssertNil(store.surfaceCue(for: counter))
        XCTAssertTrue(store.hasExplanation(for: counter))
    }

    func testTheQuestionMarkAppearsOnlyWhereThereIsAnExplanation() throws {
        let (store, _) = try makeDesk(clarification: true)
        let counter = try XCTUnwrap(store.widget(id: "push-ups-counter"))
        let tick = try XCTUnwrap(store.widget(id: "vegetables-tick"))
        XCTAssertTrue(store.hasExplanation(for: counter))
        // Vegetables carries no cue at all — no `?` on that step.
        XCTAssertFalse(store.hasExplanation(for: tick))

        let (bare, _) = try makeDesk(clarification: false)
        let bareCounter = try XCTUnwrap(bare.widget(id: "push-ups-counter"))
        // A do-time correction is not an explanation; it is already on screen.
        XCTAssertFalse(bare.hasExplanation(for: bareCounter))
    }

    // MARK: - Opening the `?` is the on-demand surface happening

    func testOpeningTheExplanationCountsSurfacedOncePerDay() throws {
        let (store, _) = try makeDesk(clarification: true)
        let before = store.snapshot.cues.first { $0.id == "push-ups-chest" }?.hits.surfaced ?? 0

        store.markExplanationsSurfaced(widgetId: "push-ups-counter")
        store.markExplanationsSurfaced(widgetId: "push-ups-counter")

        XCTAssertEqual(store.snapshot.cues.first { $0.id == "push-ups-chest" }?.hits.surfaced, before + 1)
        // The inline correction is a different place and must not be dragged along.
        XCTAssertEqual(store.snapshot.cues.first { $0.id == "push-ups-brace" }?.hits.surfaced, 0)
    }

    func testExplanationHitsSurviveRelaunch() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeDesk(clarification: true, now: now)
        store.markExplanationsSurfaced(widgetId: "push-ups-counter")
        let after = store.snapshot.cues.first { $0.id == "push-ups-chest" }?.hits.surfaced

        let reloaded = try DeskStore(repository: repository, now: { now })
        reloaded.markExplanationsSurfaced(widgetId: "push-ups-counter")

        XCTAssertEqual(reloaded.snapshot.cues.first { $0.id == "push-ups-chest" }?.hits.surfaced, after)
    }

    // MARK: - A selection with nothing to hang on stays text

    func testSelectionBindsOnlyWhatTheClientKnows() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let widgets = try SeedFactory.buildSeed(now: now).widgets

        let bound = try XCTUnwrap(
            ClarificationLaw.selection(
                quote: "keep your chest up",
                focusedWidgetId: "push-ups-counter",
                widgets: widgets
            )
        )
        XCTAssertEqual(bound.quote, "keep your chest up")
        XCTAssertEqual(bound.widgetId, "push-ups-counter")
        XCTAssertEqual(bound.subjectId, "push-ups")

        // No focused widget: the phrase travels bare. Naming a subject here
        // would be the client manufacturing the orphan cue 04 forbids.
        let unbound = try XCTUnwrap(
            ClarificationLaw.selection(quote: "keep your chest up", focusedWidgetId: nil, widgets: widgets)
        )
        XCTAssertNil(unbound.widgetId)
        XCTAssertNil(unbound.subjectId)

        // A widget that is no longer on the desk binds nothing either.
        let stale = try XCTUnwrap(
            ClarificationLaw.selection(quote: "phrase", focusedWidgetId: "gone", widgets: widgets)
        )
        XCTAssertNil(unbound.subjectId)
        XCTAssertNil(stale.widgetId)

        XCTAssertNil(ClarificationLaw.selection(quote: "   ", focusedWidgetId: "push-ups-counter", widgets: widgets))
    }

    func testAnUnboundSelectionWritesNoCue() async throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(now: now)
        let seen = LockedBox<TalkSelection?>(nil)
        let deskBeforeTurn = store.snapshot
        let client = TalkClient.stub { request in
            seen.value = request.selection
            // The service answered in text: no binding, so no cue and no
            // mutation. The client must not invent one either.
            return TalkTurnResponse(text: "It means bracing.", desk: deskBeforeTurn, mutated: false)
        }
        let talk = try makeTalk(client: client, now: now)

        let selection = ClarificationLaw.selection(
            quote: "keep your chest up",
            focusedWidgetId: talk.focusedWidgetId,
            widgets: store.snapshot.widgets
        )
        let response = await talk.send(
            utterance: SelectableAnswerText.askUtterance(quote: "keep your chest up"),
            desk: store.snapshot,
            selection: selection
        )
        store.applyTalk(try XCTUnwrap(response).desk, toolCalls: [])

        XCTAssertEqual(seen.value?.quote, "keep your chest up")
        XCTAssertNil(seen.value?.subjectId)
        XCTAssertNil(seen.value?.widgetId)
        XCTAssertEqual(store.snapshot.cues.map(\.id), deskBeforeTurn.cues.map(\.id))
        XCTAssertEqual(talk.current.messages.map(\.kind), [.user, .assistant])
    }

    func testTheUtteranceReadsAsAQuestionWhileTheQuoteStaysVerbatim() throws {
        // The drag took the sentence's full stop with it. The line the person
        // sees must not end in «.?»; what travels as `quote` is untouched.
        let quote = "don't let the hips sag."
        let utterance = SelectableAnswerText.askUtterance(quote: quote)
        XCTAssertFalse(utterance.contains(".?"))
        XCTAssertTrue(utterance.contains("don't let the hips sag"))
        let selection = try XCTUnwrap(
            ClarificationLaw.selection(
                quote: quote,
                focusedWidgetId: "push-ups-counter",
                widgets: try SeedFactory.buildSeed(now: Date()).widgets
            )
        )
        XCTAssertEqual(selection.quote, quote)
    }

    func testTurnRequestEncodesTheSelectionForTheService() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let request = TalkTurnRequest(
            utterance: "what does this mean?",
            desk: try SeedFactory.buildSeed(now: now),
            thread: [],
            focusedWidgetId: "push-ups-counter",
            selection: TalkSelection(
                quote: "keep your chest up",
                widgetId: "push-ups-counter",
                subjectId: "push-ups",
                stepId: nil
            ),
            threadId: "t1",
            now: now,
            locale: "en"
        )
        let json = try XCTUnwrap(
            JSONSerialization.jsonObject(with: try FacioJSON.encoder.encode(request)) as? [String: Any]
        )
        let selection = try XCTUnwrap(json["selection"] as? [String: Any])
        XCTAssertEqual(selection["quote"] as? String, "keep your chest up")
        XCTAssertEqual(selection["widget_id"] as? String, "push-ups-counter")
        XCTAssertEqual(selection["subject_id"] as? String, "push-ups")
        XCTAssertNil(selection["step_id"])
    }

    // MARK: - Q32: one check, after the first case

    func testTheClarityCheckIsAskedOnceAndOnlyAfterAMouthWrittenCue() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, repository) = try makeDesk(clarification: true, now: now)
        XCTAssertNil(store.clarificationAsk)

        store.completeCounter(widgetId: "push-ups-counter")
        XCTAssertEqual(store.clarificationAsk, "push-ups")

        store.markClarificationAsked(subjectId: "push-ups")
        XCTAssertNil(store.clarificationAsk)

        // A second case on the same practice never asks again.
        store.addInstance(subjectId: "push-ups")
        let widget = try XCTUnwrap(store.snapshot.widgets.last { $0.subjectId == "push-ups" })
        store.completeCounter(widgetId: widget.id)
        XCTAssertNil(store.clarificationAsk)

        // And a relaunch does not bring it back — the check was spent.
        let reloaded = try DeskStore(repository: repository, now: { now })
        reloaded.addInstance(subjectId: "push-ups")
        let third = try XCTUnwrap(reloaded.snapshot.widgets.last { $0.subjectId == "push-ups" })
        reloaded.completeCounter(widgetId: third.id)
        XCTAssertNil(reloaded.clarificationAsk)
    }

    func testAPracticeTheMouthNeverExplainedIsNeverAsked() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        // Vegetables has no cue at all; push-ups' seed correction has no origin.
        let (store, _) = try makeDesk(now: now)
        store.toggleTick(widgetId: "vegetables-tick")
        XCTAssertNil(store.clarificationAsk)
        store.completeCounter(widgetId: "push-ups-counter")
        XCTAssertNil(store.clarificationAsk)
    }

    func testTheCheckIsNotDueOnALaterCase() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let (store, _) = try makeDesk(clarification: true, now: now)
        // Once a practice has more than one closed case the check has missed
        // its moment: it belongs to the first one or to none.
        store.addInstance(subjectId: "push-ups")
        let first = try XCTUnwrap(store.snapshot.widgets.last { $0.subjectId == "push-ups" })
        store.completeCounter(widgetId: first.id)
        store.markClarificationAsked(subjectId: "push-ups")

        store.addInstance(subjectId: "push-ups")
        let second = try XCTUnwrap(store.snapshot.widgets.last { $0.subjectId == "push-ups" })
        store.completeCounter(widgetId: second.id)
        XCTAssertNil(store.clarificationAsk)
    }

    func testClarityLawCountsCompletedCasesNotWidgets() throws {
        let now = try XCTUnwrap(FacioJSON.date(from: "2026-08-16T12:00:00"))
        let cues = [
            CueLaw.addCue(
                id: "c1",
                subjectId: "push-ups",
                kind: .clarification,
                text: "chest up means…",
                origin: CueOrigin(chatId: "t1", messageId: nil)
            )
        ]
        let done = Instance(id: "i1", subjectId: "push-ups", when: now, status: .completed)
        let open = Instance(id: "i2", subjectId: "push-ups", when: now, status: .prepared)

        XCTAssertTrue(
            ClarificationLaw.asksAfterFirstCase(
                subjectId: "push-ups",
                cues: cues,
                instances: [done, open],
                alreadyAsked: false
            )
        )
        XCTAssertFalse(
            ClarificationLaw.asksAfterFirstCase(
                subjectId: "push-ups",
                cues: cues,
                instances: [done, open],
                alreadyAsked: true
            )
        )
        XCTAssertFalse(
            ClarificationLaw.asksAfterFirstCase(
                subjectId: "push-ups",
                cues: [],
                instances: [done, open],
                alreadyAsked: false
            )
        )
        XCTAssertFalse(
            ClarificationLaw.asksAfterFirstCase(
                subjectId: "push-ups",
                cues: cues,
                instances: [open],
                alreadyAsked: false
            )
        )
    }

    // MARK: - Helpers

    private func makeDesk(
        clarification: Bool = false,
        correction: Bool = true,
        now: Date = Date()
    ) throws -> (DeskStore, DeskRepository) {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-clarify-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let repository = DeskRepository(directory: directory)
        var seed = try SeedFactory.buildSeed(now: now)
        if !correction {
            seed.cues.removeAll { $0.id == "push-ups-brace" }
        }
        if clarification {
            // What the mouth writes when a phrase was selected: on-demand by
            // default, carrying the selected phrase as `quote`.
            seed.cues.append(
                CueLaw.addCue(
                    id: "push-ups-chest",
                    subjectId: "push-ups",
                    kind: .clarification,
                    text: "грудь вперёд — не сутулиться в нижней точке",
                    quote: "держи грудь",
                    origin: CueOrigin(chatId: "t1", messageId: nil)
                )
            )
        }
        try repository.saveSnapshot(seed)
        return (try DeskStore(repository: repository, now: { now }), repository)
    }

    private func makeTalk(client: TalkClient, now: Date) throws -> TalkStore {
        let directory = FileManager.default.temporaryDirectory
            .appending(path: "facio-clarify-talk-\(UUID().uuidString)", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return try TalkStore(repository: TalkRepository(directory: directory), client: client, now: { now })
    }
}

/// Small box so a `@Sendable` stub can report back what it saw.
private final class LockedBox<Value>: @unchecked Sendable {
    private let lock = NSLock()
    private var stored: Value

    init(_ value: Value) { stored = value }

    var value: Value {
        get { lock.withLock { stored } }
        set { lock.withLock { stored = newValue } }
    }
}
