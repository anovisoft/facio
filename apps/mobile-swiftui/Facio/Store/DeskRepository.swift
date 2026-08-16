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
