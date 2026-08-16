import SwiftUI

struct AtmosphereBackground: View {
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        ZStack {
            LinearGradient(
                colors: [
                    FacioTheme.atmosphereTop(for: colorScheme),
                    FacioTheme.atmosphereBottom(for: colorScheme),
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            RadialGradient(
                colors: [FacioTheme.warmSpot(for: colorScheme), Color.clear],
                center: UnitPoint(x: 0.10, y: 0.06),
                startRadius: 8,
                endRadius: 360
            )
            RadialGradient(
                colors: [FacioTheme.coolSpot(for: colorScheme), Color.clear],
                center: UnitPoint(x: 0.94, y: 0.28),
                startRadius: 16,
                endRadius: 400
            )
            RadialGradient(
                colors: [FacioTheme.roseSpot(for: colorScheme), Color.clear],
                center: UnitPoint(x: 0.48, y: 0.96),
                startRadius: 24,
                endRadius: 440
            )
        }
        .ignoresSafeArea()
        .allowsHitTesting(false)
        .accessibilityHidden(true)
    }
}
