import Foundation

/// `GET`/`PUT /v1/desk` — the server copy of the desk, once signed in.
/// Separate from `TalkClient`: talk stays stateless/unauthenticated (В3.1
/// leaves `/v1/talk/turn` untouched), this is the sync-only surface.
struct DeskClient: Sendable {
    var baseURL: URL
    var session: URLSession
    /// Shorter than the talk timeout: nobody waits a minute to learn the
    /// sync did not go through, and the desk is fine either way.
    var timeout: TimeInterval
    var fetchHandler: (@Sendable (String) async throws -> DeskSnapshot?)?
    var pushHandler: (@Sendable (DeskSnapshot, String) async throws -> DeskSnapshot)?

    static func live() -> DeskClient {
        DeskClient(
            baseURL: TalkClient.configuredBaseURL(),
            session: .shared,
            timeout: 15,
            fetchHandler: nil,
            pushHandler: nil
        )
    }

    static func stub(
        fetch: @escaping @Sendable (String) async throws -> DeskSnapshot?,
        push: @escaping @Sendable (DeskSnapshot, String) async throws -> DeskSnapshot
    ) -> DeskClient {
        DeskClient(
            baseURL: URL(string: "http://127.0.0.1:8000")!,
            session: .shared,
            timeout: 15,
            fetchHandler: fetch,
            pushHandler: push
        )
    }

    func fetch(sessionToken: String) async throws -> DeskSnapshot? {
        if let fetchHandler {
            return try await fetchHandler(sessionToken)
        }
        var request = URLRequest(url: baseURL.appending(path: "v1/desk"))
        request.timeoutInterval = timeout
        request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw TalkClientError.transport }
        if http.statusCode == 404 { return nil }
        guard (200 ..< 300).contains(http.statusCode) else { throw TalkClientError.http(http.statusCode) }
        do {
            return try FacioJSON.decoder.decode(DeskSnapshot.self, from: data)
        } catch {
            throw TalkClientError.decoding
        }
    }

    @discardableResult
    func push(_ snapshot: DeskSnapshot, sessionToken: String) async throws -> DeskSnapshot {
        if let pushHandler {
            return try await pushHandler(snapshot, sessionToken)
        }
        var request = URLRequest(url: baseURL.appending(path: "v1/desk"))
        request.httpMethod = "PUT"
        request.timeoutInterval = timeout
        request.setValue("Bearer \(sessionToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try FacioJSON.encoder.encode(snapshot)
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else { throw TalkClientError.transport }
        guard (200 ..< 300).contains(http.statusCode) else { throw TalkClientError.http(http.statusCode) }
        do {
            return try FacioJSON.decoder.decode(DeskSnapshot.self, from: data)
        } catch {
            throw TalkClientError.decoding
        }
    }
}
