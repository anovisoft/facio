import XCTest
@testable import Facio

/// Guards the two string catalogs. The client ships `ru` and `en`; the PM runs
/// the simulator with `-AppleLanguages "(en)"`, so a key without a finished
/// `en` translation is a hole on screen, not a nit. Reads the catalog sources
/// from the repo (no network, no server).
final class LocalizationCatalogTests: XCTestCase {
    private static let languages = ["ru", "en"]

    func testLocalizableCatalogIsFullyTranslated() throws {
        try assertFullyTranslated(catalog: "Localizable")
    }

    func testInfoPlistCatalogIsFullyTranslated() throws {
        try assertFullyTranslated(catalog: "InfoPlist")
    }

    func testLocalizableCatalogCarriesTheLidSections() throws {
        let catalog = try catalog(named: "Localizable")
        // The English voice comes from docs/rfc/03-product.md. If someone
        // retranslates the lid, these are the words the RFC uses.
        let expected: [String: String] = [
            "Сегодня": "Today",
            "Lifetime": "Lifetime",
            "В ближайшее время": "Soon",
            "Отложили": "Postponed",
            "Что сюда на стол?": "What belongs on the table?",
            "ничего на сегодня — и это нормально": "nothing for today — and that's fine",
        ]
        for (key, english) in expected {
            XCTAssertEqual(catalog.value(of: key, in: "en"), english, "key \(key)")
        }
    }

    /// Every catalog key must survive the trip through the built app bundle,
    /// in both languages. Catches a catalog that parses but never gets compiled
    /// into `en.lproj` / `ru.lproj`.
    func testBuiltBundleCarriesBothLanguages() throws {
        let appBundle = Bundle(for: DeskStore.self)
        let catalog = try catalog(named: "Localizable")
        let sentinel = "⟂missing⟂"
        for language in Self.languages {
            let path = try XCTUnwrap(
                appBundle.path(forResource: language, ofType: "lproj"),
                "app bundle has no \(language).lproj"
            )
            let strings = try XCTUnwrap(Bundle(path: path), "unreadable \(language).lproj")
            for key in catalog.keys {
                let value = strings.localizedString(forKey: key, value: sentinel, table: nil)
                XCTAssertNotEqual(value, sentinel, "\(language) is missing key \(key)")
                XCTAssertFalse(value.isEmpty, "\(language) has an empty value for key \(key)")
            }
        }
    }

    // MARK: - Helpers

    private func assertFullyTranslated(catalog name: String, file: StaticString = #filePath, line: UInt = #line) throws {
        let catalog = try catalog(named: name)
        XCTAssertEqual(catalog.sourceLanguage, "ru", "\(name): source language moved", file: file, line: line)
        XCTAssertFalse(catalog.keys.isEmpty, "\(name): catalog is empty", file: file, line: line)
        for key in catalog.keys.sorted() {
            if catalog.shouldTranslate(key) == false { continue }
            for language in Self.languages {
                guard let unit = catalog.unit(of: key, in: language) else {
                    XCTFail("\(name): key \(key) has no \(language) translation", file: file, line: line)
                    continue
                }
                XCTAssertEqual(
                    unit.state,
                    "translated",
                    "\(name): key \(key) is \(unit.state) in \(language)",
                    file: file,
                    line: line
                )
                XCTAssertFalse(
                    unit.value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                    "\(name): key \(key) is empty in \(language)",
                    file: file,
                    line: line
                )
            }
        }
    }

    private func catalog(named name: String) throws -> StringCatalog {
        let url = Self.resourcesDirectory.appending(path: "\(name).xcstrings")
        guard FileManager.default.fileExists(atPath: url.path) else {
            throw CatalogError.missingCatalog(url.path)
        }
        return try StringCatalog(url: url)
    }

    /// `apps/mobile-swiftui/Facio/Resources`, relative to this test file.
    private static let resourcesDirectory: URL = {
        URL(filePath: #filePath)          // .../FacioTests/LocalizationCatalogTests.swift
            .deletingLastPathComponent()  // .../FacioTests
            .deletingLastPathComponent()  // .../mobile-swiftui
            .appending(path: "Facio")
            .appending(path: "Resources")
    }()
}

private enum CatalogError: Error, CustomStringConvertible {
    case missingCatalog(String)
    case badShape(String)

    var description: String {
        switch self {
        case .missingCatalog(let path): "no string catalog at \(path)"
        case .badShape(let detail): "unexpected string catalog shape: \(detail)"
        }
    }
}

private struct StringCatalog {
    struct Unit {
        let state: String
        let value: String
    }

    let sourceLanguage: String
    let keys: [String]
    private let strings: [String: [String: Any]]

    init(url: URL) throws {
        let raw = try JSONSerialization.jsonObject(with: Data(contentsOf: url))
        guard let root = raw as? [String: Any],
              let sourceLanguage = root["sourceLanguage"] as? String,
              let strings = root["strings"] as? [String: [String: Any]]
        else {
            throw CatalogError.badShape(url.lastPathComponent)
        }
        self.sourceLanguage = sourceLanguage
        self.strings = strings
        self.keys = Array(strings.keys)
    }

    func shouldTranslate(_ key: String) -> Bool? {
        strings[key]?["shouldTranslate"] as? Bool
    }

    func unit(of key: String, in language: String) -> Unit? {
        guard let entry = strings[key],
              let localizations = entry["localizations"] as? [String: Any],
              let localization = localizations[language] as? [String: Any],
              let unit = localization["stringUnit"] as? [String: Any],
              let state = unit["state"] as? String,
              let value = unit["value"] as? String
        else { return nil }
        return Unit(state: state, value: value)
    }

    func value(of key: String, in language: String) -> String? {
        unit(of: key, in: language)?.value
    }
}
