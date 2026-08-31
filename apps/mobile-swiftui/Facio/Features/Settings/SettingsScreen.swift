import AuthenticationServices
import SwiftUI

/// Bottom of the pan (03-product): who is signed in, one button, one line
/// about the sync, the version. No stats, no achievements — those are "later".
/// Not a tab and not a second home: it opens from the pan and closes back.
struct SettingsScreen: View {
    let sync: DeskSyncCoordinator
    var onClose: () -> Void

    @Environment(\.colorScheme) private var colorScheme
    @State private var signInFailed = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    accountRow
                    if sync.isSignedIn {
                        Button(role: .destructive) {
                            sync.signOut()
                            signInFailed = false
                        } label: {
                            Text("Выйти")
                        }
                    } else {
                        signInButton
                    }
                } header: {
                    Text("Аккаунт")
                } footer: {
                    if signInFailed {
                        Text("Вход сейчас не проходит. Крышка работает.")
                    } else if sync.isSignedIn {
                        Text("Выход не стирает стол — он остаётся на устройстве.")
                    } else {
                        Text("Вход не обязателен: без него всё работает на устройстве.")
                    }
                }

                Section {
                    LabeledContent {
                        Text(version)
                            .foregroundStyle(.secondary)
                    } label: {
                        Text("Версия")
                    }
                }
            }
            .navigationTitle(Text("Настройки"))
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(action: onClose) {
                        Text("Готово")
                    }
                }
            }
        }
    }

    private var accountRow: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(accountTitle)
                .font(.body)
                .foregroundStyle(.primary)
            Text(syncLine)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
    }

    private var signInButton: some View {
        SignInWithAppleButton(.signIn) { request in
            request.requestedScopes = [.fullName]
        } onCompletion: { result in
            handle(result)
        }
        .signInWithAppleButtonStyle(colorScheme == .dark ? .white : .black)
        .frame(height: 48)
        .listRowInsets(EdgeInsets(top: 8, leading: 16, bottom: 8, trailing: 16))
    }

    private var accountTitle: String {
        guard let session = sync.session else {
            return String(localized: "Вход не выполнен", comment: "Settings: signed out")
        }
        if let name = session.displayName, !name.isEmpty {
            return name
        }
        return String(localized: "Аккаунт Apple", comment: "Settings: signed in without a name")
    }

    private var syncLine: String {
        guard let session = sync.session else {
            return String(localized: "только на устройстве", comment: "Settings: no account, desk is local")
        }
        if sync.isBusy {
            return String(localized: "синк идёт", comment: "Settings: sync in flight")
        }
        if sync.offline {
            return String(localized: "синк без сети", comment: "Settings: sync could not reach the server")
        }
        guard let stamp = session.lastSyncedAt else {
            return String(localized: "синка ещё не было", comment: "Settings: signed in, never synced")
        }
        let when = stamp.formatted(date: .abbreviated, time: .shortened)
        return String(localized: "последний синк \(when)", comment: "Settings: last sync stamp")
    }

    /// `MARKETING_VERSION` through `Info.plist` — never a hardcoded 1.0.
    private var version: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"
    }

    private func handle(_ result: Result<ASAuthorization, Error>) {
        switch result {
        case .success(let authorization):
            guard let credential = authorization.credential as? ASAuthorizationAppleIDCredential,
                  let data = credential.identityToken,
                  let token = String(data: data, encoding: .utf8)
            else {
                signInFailed = true
                return
            }
            let name = credential.fullName.map {
                PersonNameComponentsFormatter.localizedString(from: $0, style: .default)
            }
            Task {
                do {
                    try await sync.signIn(
                        identityToken: token,
                        displayName: (name?.isEmpty == false) ? name : nil
                    )
                    signInFailed = false
                } catch {
                    // Network or a server that does not know this token yet:
                    // one quiet line, never a catastrophe modal.
                    signInFailed = true
                }
            }
        case .failure(let error):
            // Cancelling is silent — the user closed the sheet, nothing broke.
            if let authError = error as? ASAuthorizationError, authError.code == .canceled {
                return
            }
            signInFailed = true
        }
    }
}
