import SwiftUI

enum FacioTheme {
    static func atmosphereTop(for scheme: ColorScheme) -> Color {
        switch scheme {
        case .dark:
            Color(red: 0.18, green: 0.15, blue: 0.13)
        default:
            Color(red: 0.88, green: 0.85, blue: 0.80)
        }
    }

    static func atmosphereBottom(for scheme: ColorScheme) -> Color {
        switch scheme {
        case .dark:
            Color(red: 0.07, green: 0.10, blue: 0.16)
        default:
            Color(red: 0.68, green: 0.74, blue: 0.82)
        }
    }

    static func warmSpot(for scheme: ColorScheme) -> Color {
        switch scheme {
        case .dark:
            Color(red: 0.48, green: 0.34, blue: 0.24).opacity(0.55)
        default:
            Color(red: 0.96, green: 0.86, blue: 0.74).opacity(0.70)
        }
    }

    static func coolSpot(for scheme: ColorScheme) -> Color {
        switch scheme {
        case .dark:
            Color(red: 0.20, green: 0.34, blue: 0.56).opacity(0.50)
        default:
            Color(red: 0.58, green: 0.70, blue: 0.88).opacity(0.55)
        }
    }

    static func roseSpot(for scheme: ColorScheme) -> Color {
        switch scheme {
        case .dark:
            Color(red: 0.42, green: 0.24, blue: 0.38).opacity(0.40)
        default:
            Color(red: 0.90, green: 0.78, blue: 0.86).opacity(0.45)
        }
    }
}

struct FacioChrome: ViewModifier {
    func body(content: Content) -> some View {
        content
            .toolbarBackground(.hidden, for: .navigationBar)
            .containerBackground(for: .navigation) {
                AtmosphereBackground()
            }
            .modifier(FacioScrollEdge())
    }
}

private struct FacioScrollEdge: ViewModifier {
    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            content.scrollEdgeEffectStyle(.soft, for: .top)
        } else {
            content
        }
    }
}

extension View {
    func facioChrome() -> some View {
        modifier(FacioChrome())
    }
}
