import Foundation

enum CueMedia: Codable, Sendable, Equatable {
    case photo(ref: String)
    case link(url: String)

    var kind: String {
        switch self {
        case .photo: "photo"
        case .link: "link"
        }
    }

    private enum CodingKeys: String, CodingKey {
        case kind
        case ref
        case url
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let kind = try container.decode(String.self, forKey: .kind)
        switch kind {
        case "photo":
            self = .photo(ref: try container.decode(String.self, forKey: .ref))
        case "link":
            self = .link(url: try container.decode(String.self, forKey: .url))
        default:
            throw DecodingError.dataCorruptedError(forKey: .kind, in: container, debugDescription: kind)
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        switch self {
        case .photo(let ref):
            try container.encode("photo", forKey: .kind)
            try container.encode(ref, forKey: .ref)
        case .link(let url):
            try container.encode("link", forKey: .kind)
            try container.encode(url, forKey: .url)
        }
    }
}
