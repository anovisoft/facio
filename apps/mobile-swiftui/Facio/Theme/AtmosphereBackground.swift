import SwiftUI

struct AtmosphereBackground: View {
    var body: some View {
        ZStack {
            Color(red: 0.78, green: 0.80, blue: 0.84)
            RadialGradient(
                colors: [
                    Color(red: 0.93, green: 0.86, blue: 0.78).opacity(0.95),
                    Color.clear,
                ],
                center: UnitPoint(x: 0.12, y: 0.08),
                startRadius: 10,
                endRadius: 380
            )
            RadialGradient(
                colors: [
                    Color(red: 0.62, green: 0.70, blue: 0.82).opacity(0.85),
                    Color.clear,
                ],
                center: UnitPoint(x: 0.92, y: 0.22),
                startRadius: 20,
                endRadius: 420
            )
            RadialGradient(
                colors: [
                    Color(red: 0.88, green: 0.80, blue: 0.86).opacity(0.55),
                    Color.clear,
                ],
                center: UnitPoint(x: 0.55, y: 0.92),
                startRadius: 40,
                endRadius: 480
            )
        }
        .ignoresSafeArea()
    }
}
