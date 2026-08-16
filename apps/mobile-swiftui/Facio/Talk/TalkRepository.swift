import Foundation

struct TalkRepository: Sendable {
    private let directory: URL

    init(directory: URL) {
        self.directory = directory
    }

    static func applicationSupport() throws -> TalkRepository {
        let root = try FileManager.default.url(
            for: .applicationSupportDirectory,
            in: .userDomainMask,
            appropriateFor: nil,
            create: true
        )
        let directory = root.appending(path: "Facio", directoryHint: .isDirectory)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return TalkRepository(directory: directory)
    }

    private var url: URL { directory.appending(path: "talks.json") }

    func load(now: Date) throws -> TalkArchive {
        guard FileManager.default.fileExists(atPath: url.path) else {
            return TalkArchive(current: .empty(now: now), archived: [])
        }
        let data = try Data(contentsOf: url)
        return try FacioJSON.decoder.decode(TalkArchive.self, from: data)
    }

    func save(_ archive: TalkArchive) throws {
        let data = try FacioJSON.encoder.encode(archive)
        let temporary = url.appendingPathExtension("tmp")
        try data.write(to: temporary, options: .atomic)
        if FileManager.default.fileExists(atPath: url.path) {
            _ = try FileManager.default.replaceItemAt(url, withItemAt: temporary)
        } else {
            try FileManager.default.moveItem(at: temporary, to: url)
        }
    }
}
