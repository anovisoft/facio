import Foundation

struct TalkClient: Sendable {
    var baseURL: URL
    var session: URLSession
    var timeout: TimeInterval
    var turnHandler: (@Sendable (TalkTurnRequest) async throws -> TalkTurnResponse)?

    static func live() -> TalkClient {
        TalkClient(
            baseURL: TalkClient.configuredBaseURL(),
            session: .shared,
            timeout: 60,
            turnHandler: nil
        )
    }

    static func stub(_ handler: @escaping @Sendable (TalkTurnRequest) async throws -> TalkTurnResponse) -> TalkClient {
        TalkClient(
            baseURL: URL(string: "http://127.0.0.1:8000")!,
            session: .shared,
            timeout: 60,
            turnHandler: handler
        )
    }

    static func configuredBaseURL() -> URL {
        if let raw = Bundle.main.object(forInfoDictionaryKey: "FacioTalkURL") as? String,
           let url = URL(string: raw),
           !raw.isEmpty
        {
            return url
        }
        return URL(string: "http://127.0.0.1:8000")!
    }

    func turn(_ request: TalkTurnRequest) async throws -> TalkTurnResponse {
        if let turnHandler {
            return try await turnHandler(request)
        }
        var urlRequest = URLRequest(url: baseURL.appending(path: "v1/talk/turn"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.timeoutInterval = timeout
        urlRequest.httpBody = try FacioJSON.encoder.encode(request)
        let (data, response) = try await session.data(for: urlRequest)
        guard let http = response as? HTTPURLResponse else {
            throw TalkClientError.transport
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            throw TalkClientError.http(http.statusCode)
        }
        do {
            return try FacioJSON.decoder.decode(TalkTurnResponse.self, from: data)
        } catch {
            throw TalkClientError.decoding
        }
    }
}

enum TalkClientError: Error, Equatable {
    case transport
    case http(Int)
    case decoding
}
