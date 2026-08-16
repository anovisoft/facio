import Foundation

enum CueError: Error, Equatable {
    case surfaceRequired
    case quoteMustBeText
}

struct Cue: Codable, Sendable, Equatable, Identifiable {
    var id: String
    var subjectId: String
    var stepId: String?
    var kind: CueKind
    var text: String
    var quote: String?
    var media: CueMedia?
    var origin: CueOrigin?
    var surface: CueSurface
    var hits: CueHits

    enum CodingKeys: String, CodingKey {
        case id
        case subjectId = "subject_id"
        case stepId = "step_id"
        case kind
        case text
        case quote
        case media
        case origin
        case surface
        case hits
    }

    init(
        id: String,
        subjectId: String,
        stepId: String? = nil,
        kind: CueKind,
        text: String,
        quote: String? = nil,
        media: CueMedia? = nil,
        origin: CueOrigin? = nil,
        surface: CueSurface,
        hits: CueHits = CueHits()
    ) {
        self.id = id
        self.subjectId = subjectId
        self.stepId = stepId
        self.kind = kind
        self.text = text
        self.quote = quote
        self.media = media
        self.origin = origin
        self.surface = surface
        self.hits = hits
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        guard container.contains(.surface) else { throw CueError.surfaceRequired }
        id = try container.decode(String.self, forKey: .id)
        subjectId = try container.decode(String.self, forKey: .subjectId)
        stepId = try container.decodeIfPresent(String.self, forKey: .stepId)
        kind = try container.decode(CueKind.self, forKey: .kind)
        text = try container.decode(String.self, forKey: .text)
        if container.contains(.quote), try container.decodeNil(forKey: .quote) == false {
            do {
                quote = try container.decode(String.self, forKey: .quote)
            } catch {
                throw CueError.quoteMustBeText
            }
        } else {
            quote = nil
        }
        media = try container.decodeIfPresent(CueMedia.self, forKey: .media)
        origin = try container.decodeIfPresent(CueOrigin.self, forKey: .origin)
        surface = try container.decode(CueSurface.self, forKey: .surface)
        hits = try container.decodeIfPresent(CueHits.self, forKey: .hits) ?? CueHits()
    }
}
