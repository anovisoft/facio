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
