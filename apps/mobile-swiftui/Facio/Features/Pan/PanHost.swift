import SwiftUI
import UIKit

struct PanHost<Content: View>: View {
    @Bindable var pan: PanSession
    var enabled: Bool
    @ViewBuilder var panContent: () -> PanScreen
    @ViewBuilder var content: () -> Content
    @State private var hostWidth: CGFloat = 390

    var body: some View {
        let width = min(FacioPalette.panMaxWidth, hostWidth * FacioPalette.panWidthRatio)
        let revealed = enabled ? pan.revealed(width: width) : 0
        let progress = min(1, revealed / max(width, 1))
        let radius = FacioPalette.deviceCornerRadius * progress
        let card = RoundedRectangle(cornerRadius: radius, style: .continuous)

        ZStack(alignment: .leading) {
            AtmosphereBackground()
            panContent()
                .frame(width: width, alignment: .topLeading)
                .frame(maxHeight: .infinity, alignment: .top)
                .contentShape(Rectangle())
                .allowsHitTesting(revealed > 8)
                .accessibilityHidden(revealed < 12)
                .zIndex(revealed > 8 ? 2 : 0)
            content()
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .overlay {
                    if revealed > 0 {
                        Color.black.opacity(0.2 * Double(progress))
                            .ignoresSafeArea()
                            .onTapGesture { pan.close() }
                            .gesture(closeDrag(width: width))
                            .accessibilityLabel("Закрыть сковородку")
                            .accessibilityAddTraits(.isButton)
                    }
                }
                .compositingGroup()
                .clipShape(card)
                .shadow(color: .black.opacity(0.22 * progress), radius: 28, x: -6, y: 0)
                .offset(x: revealed)
                .zIndex(1)
        }
        .ignoresSafeArea()
        .animation(.spring(response: 0.38, dampingFraction: 0.86), value: pan.isOpen)
        .environment(\.panWidth, width)
        .background {
            GeometryReader { geo in
                Color.clear
                    .onAppear { hostWidth = geo.size.width }
                    .onChange(of: geo.size.width) { _, value in
                        hostWidth = value
                    }
            }
        }
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
