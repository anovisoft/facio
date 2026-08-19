import SwiftUI
import UIKit

struct PanHost<Content: View>: View {
    @Bindable var pan: PanSession
    var enabled: Bool
    @ViewBuilder var panContent: () -> PanScreen
    @ViewBuilder var content: () -> Content

    var body: some View {
        let width = min(FacioPalette.panMaxWidth, FacioPalette.deviceWidth * FacioPalette.panWidthRatio)
        let revealed = enabled ? pan.revealed(width: width) : 0
        let progress = min(1, revealed / max(width, 1))
        let radius = FacioPalette.deviceCornerRadius * progress
        let card = RoundedRectangle(cornerRadius: radius, style: .continuous)
        let insets = FacioPalette.deviceSafeArea

        ZStack {
            AtmosphereBackground()
            PanSlideLayout(panWidth: width, revealed: revealed) {
                panContent()
                    .padding(.top, insets.top)
                    .padding(.bottom, insets.bottom)
                    .clipped()
                    .contentShape(Rectangle())
                    .allowsHitTesting(revealed > 8)
                    .accessibilityHidden(revealed < 12)
                content()
                    .overlay {
                        Color.black.opacity(0.2 * Double(progress))
                            .allowsHitTesting(revealed > 8)
                            .onTapGesture { pan.close() }
                            .gesture(closeDrag(width: width))
                            .accessibilityLabel("Закрыть сковородку")
                            .accessibilityAddTraits(.isButton)
                            .accessibilityHidden(revealed < 8)
                    }
                    .compositingGroup()
                    .clipShape(card)
                    .shadow(color: .black.opacity(0.22 * progress), radius: 28, x: -6, y: 0)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .clipped()
        .ignoresSafeArea()
        .animation(.spring(response: 0.38, dampingFraction: 0.86), value: pan.isOpen)
        .environment(\.panWidth, width)
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillShowNotification)) { _ in
            pan.keyboardUp = true
        }
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillHideNotification)) { _ in
            pan.keyboardUp = false
        }
    }

    private func closeDrag(width: CGFloat) -> some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .global)
            .onChanged { value in
                guard abs(value.translation.width) >= abs(value.translation.height) else { return }
                pan.drag = value.translation.width
            }
            .onEnded { value in
                pan.endDrag(
                    translation: value.translation.width,
                    predicted: value.predictedEndTranslation.width,
                    width: width
                )
            }
    }
}
