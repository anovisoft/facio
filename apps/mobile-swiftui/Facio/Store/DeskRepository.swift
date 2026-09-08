import Foundation

struct DeskRepository: Sendable {
    private let directory: URL

    init(directory: URL) {
        self.directory = directory
    }

    static func applicationSupport() throws -> DeskRepository {
        let root = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let directory = root.appending(path: "Facio", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return DeskRepository(directory: directory)
    }

    private var snapshotURL: URL { directory.appending(path: "desk.json") }
    private var journalURL: URL { directory.appending(path: "journal.jsonl") }
    private var dayZeroURL: URL { directory.appending(path: "day-zero.closed") }
    private var undoURL: URL { directory.appending(path: "undo.json") }

    /// Day zero happens once. The latch is a marker file next to `desk.json`
    /// on purpose: `desk.json` is the wire shape the service also writes, and a
    /// client-only "he has seen the chips" flag has no business travelling on it.
    func dayZeroClosed() -> Bool {
        FileManager.default.fileExists(atPath: dayZeroURL.path)
    }

    func closeDayZero() {
        guard !dayZeroClosed() else { return }
        try? Data().write(to: dayZeroURL, options: .atomic)
    }

    func loadSnapshot() throws -> DeskSnapshot? {
        guard FileManager.default.fileExists(atPath: snapshotURL.path) else { return nil }
        let data = try Data(contentsOf: snapshotURL)
        return try FacioJSON.decoder.decode(DeskSnapshot.self, from: data)
    }

    func saveSnapshot(_ snapshot: DeskSnapshot) throws {
        let data = try FacioJSON.encoder.encode(snapshot)
        let temporary = snapshotURL.appendingPathExtension("tmp")
        try data.write(to: temporary, options: .atomic)
        if FileManager.default.fileExists(atPath: snapshotURL.path) {
            _ = try FileManager.default.replaceItemAt(snapshotURL, withItemAt: temporary)
        } else {
            try FileManager.default.moveItem(at: temporary, to: snapshotURL)
        }
    }

    /// The one step back, beside `desk.json` and not inside it: the snapshot is
    /// the wire shape the service also writes, and «this device can still undo
    /// that turn» is this device's business — the same reason day zero is a
    /// latch file. It lives on disk rather than in memory because the offer is
    /// visible in a thread that survives a relaunch: a button that stopped
    /// working while it was still on screen is «no undo» with extra steps.
    func loadUndo() -> UndoableTurn? {
        guard FileManager.default.fileExists(atPath: undoURL.path),
              let data = try? Data(contentsOf: undoURL)
        else { return nil }
        return try? FacioJSON.decoder.decode(UndoableTurn.self, from: data)
    }

    func saveUndo(_ record: UndoableTurn) {
        guard let data = try? FacioJSON.encoder.encode(record) else { return }
        try? data.write(to: undoURL, options: .atomic)
    }

    func clearUndo() {
        try? FileManager.default.removeItem(at: undoURL)
    }

    /// The journal from `since` onwards, oldest first.
    ///
    /// Read **on demand**, never at launch: the whole point of `journal.jsonl`
    /// is that it grows for ever, and a cold start that decodes a year of it
    /// spun the cue counters on a phone once already. The measurement sheet is
    /// the only caller that wants the whole file, and it wants it once, while
    /// the person is looking at it.
    ///
    /// A line that does not decode is skipped, not fatal: a half-written last
    /// line after a kill is the normal end of an append-only file.
    func journal(since: Date? = nil) -> [JournalEvent] {
        guard FileManager.default.fileExists(atPath: journalURL.path),
              let data = try? Data(contentsOf: journalURL),
              let text = String(data: data, encoding: .utf8)
        else { return [] }
        var events: [JournalEvent] = []
        for line in text.split(whereSeparator: \.isNewline) {
            guard let event = try? FacioJSON.decoder.decode(JournalEvent.self, from: Data(line.utf8))
            else { continue }
            if let since, event.at < since { continue }
            events.append(event)
        }
        return events.sorted { $0.at < $1.at }
    }

    /// Which practices already had their drift card written down today. Same
    /// shape as `surfacedPlaces`, and for the same reason: a card is on screen
    /// for as long as the person leaves it there, and `onAppear` fires on every
    /// scroll — the journal must count the ask, not the redraw.
    func driftSurfacedSubjects(on day: Date) -> Set<String> {
        let start = Calendar.current.startOfDay(for: day)
        guard let end = Calendar.current.date(byAdding: .day, value: 1, to: start) else { return [] }
        return Set(
            journal(since: start)
                .filter { $0.type == .driftSurfaced && $0.at < end }
                .compactMap(\.subjectId)
        )
    }

    func surfacedPlaces(on day: Date) -> Set<String> {
        guard FileManager.default.fileExists(atPath: journalURL.path),
              let data = try? Data(contentsOf: journalURL),
              let text = String(data: data, encoding: .utf8)
        else { return [] }
        let start = Calendar.current.startOfDay(for: day)
        guard let end = Calendar.current.date(byAdding: .day, value: 1, to: start) else { return [] }
        var places: Set<String> = []
        for line in text.split(whereSeparator: \.isNewline) {
            guard let event = try? FacioJSON.decoder.decode(JournalEvent.self, from: Data(line.utf8)),
                  event.type == .cueSurfaced,
                  event.at >= start,
                  event.at < end,
                  let widgetId = event.widgetId,
                  let place = event.payload?["place"]
            else { continue }
            places.insert("\(widgetId)|\(place)")
        }
        return places
    }

    /// Subjects whose one clarity check (Q32) has already been spent. Read once
    /// at launch, like the surfaced places above — asking again after a
    /// relaunch would make the "one check" a habit.
    func clarificationAskedSubjects() -> Set<String> {
        guard FileManager.default.fileExists(atPath: journalURL.path),
              let data = try? Data(contentsOf: journalURL),
              let text = String(data: data, encoding: .utf8)
        else { return [] }
        var subjects: Set<String> = []
        for line in text.split(whereSeparator: \.isNewline) {
            guard let event = try? FacioJSON.decoder.decode(JournalEvent.self, from: Data(line.utf8)),
                  event.type == .clarificationAsked,
                  let subjectId = event.subjectId
            else { continue }
            subjects.insert(subjectId)
        }
        return subjects
    }

    func append(_ event: JournalEvent) throws {
        var data = try FacioJSON.encoder.encode(event)
        data.append(0x0A)
        if FileManager.default.fileExists(atPath: journalURL.path) {
            let handle = try FileHandle(forWritingTo: journalURL)
            defer { try? handle.close() }
            try handle.seekToEnd()
            try handle.write(contentsOf: data)
        } else {
            try data.write(to: journalURL, options: .atomic)
        }
    }
}
