import Foundation
@testable import Facio

enum DomainFixtures {
    static func decode<T: Decodable>(_ name: String, as type: T.Type = T.self) throws -> T {
        let bundle = Bundle(for: BundleToken.self)
        guard let url = bundle.url(forResource: name, withExtension: "json") else {
            throw FixtureError.missingResource(name)
        }
        return try FacioJSON.decoder.decode(T.self, from: Data(contentsOf: url))
    }

    static func subjects() throws -> [Subject] { try decode("subjects") }
    static func cues() throws -> [Cue] { try decode("cues") }
    static func widgets() throws -> [Widget] { try decode("widgets") }
    static func scenarios() throws -> ScenarioFile { try decode("scenarios") }

    static func now() throws -> Date {
        let raw = try scenarios().now
        guard let date = FacioJSON.date(from: raw) else { throw FixtureError.badDate(raw) }
        return date
    }

    static func subject(_ id: String) throws -> Subject {
        guard let subject = try subjects().first(where: { $0.id == id }) else {
            throw FixtureError.missingSubject(id)
        }
        return subject
    }
}

private final class BundleToken {}

enum FixtureError: Error {
    case missingResource(String)
    case missingSubject(String)
    case badDate(String)
}

struct ScenarioFile: Decodable {
    var now: String
    var bikeSilence: [BikeSilenceCase]
    var emptyTodayNoCommitments: ScenarioCase
    var emptyTodayWithDrift: ScenarioCase
    var missTuesday: ScenarioCase

    enum CodingKeys: String, CodingKey {
        case now
        case bikeSilence = "bike_silence"
        case emptyTodayNoCommitments = "empty_today_no_commitments"
        case emptyTodayWithDrift = "empty_today_with_drift"
        case missTuesday = "miss_tuesday"
    }
}

struct BikeSilenceCase: Decodable {
    var id: String
    var lastCompleted: String
    var expectDrifting: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case lastCompleted = "last_completed"
        case expectDrifting = "expect_drifting"
    }
}

struct ScenarioCase: Decodable {
    var instances: [Instance]
}
