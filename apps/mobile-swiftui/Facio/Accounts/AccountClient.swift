import Foundation

struct AccountClient: Sendable {
    var baseURL: URL
    var session: URLSession
    var signInHandler: (@Sendable (AppleSignInRequest) async throws -> AppleSignInResponse)?

    static func live() -> AccountClient {
        AccountClient(baseURL: TalkClient.configuredBaseURL(), session: .shared, signInHandler: nil)
    }

    static func stub(_ handler: @escaping @Sendable (AppleSignInRequest) async throws -> AppleSignInResponse) -> AccountClient {
        AccountClient(baseURL: URL(string: "http://127.0.0.1:8000")!, session: .shared, signInHandler: handler)
    }

    func signIn(identityToken: String) async throws -> AppleSignInResponse {
        let request = AppleSignInRequest(identityToken: identityToken)
        if let signInHandler {
            return try await signInHandler(request)
        }
        var urlRequest = URLRequest(url: baseURL.appending(path: "v1/auth/apple"))
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try FacioJSON.encoder.encode(request)
        let (data, response) = try await session.data(for: urlRequest)
        guard let http = response as? HTTPURLResponse else {
            throw TalkClientError.transport
        }
        guard (200 ..< 300).contains(http.statusCode) else {
            throw TalkClientError.http(http.statusCode)
        }
        do {
            return try FacioJSON.decoder.decode(AppleSignInResponse.self, from: data)
        } catch {
            throw TalkClientError.decoding
        }
    }
}
