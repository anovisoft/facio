import SwiftUI
import UIKit

struct PanHost<Content: View>: View {
    @Bindable var pan: PanSession
    var enabled: Bool
    @ViewBuilder var panContent: () -> PanScreen
    @ViewBuilder var content: () -> Content

    var body: some View {
        let panWidth = PanSlideLaw.panWidth(
            containerWidth: WindowMetrics.width,
            maxWidth: FacioPalette.panMaxWidth,
            ratio: FacioPalette.panWidthRatio
        )
        let revealed = enabled
            ? PanSlideLaw.revealed(isOpen: pan.isOpen, drag: pan.drag, panWidth: panWidth)
            : 0
        let progress = PanSlideLaw.progress(revealed: revealed, panWidth: panWidth)
        let radius = PanSlideLaw.cardRadius(
            progress: progress,
            deviceRadius: WindowMetrics.displayCornerRadius
        )
        let insets = WindowMetrics.safeArea

        ZStack {
            // Opaque NavigationStack chrome hides containerBackground; this copy
            // fills the pan gap and the first launch. Do not drop either layer.
            AtmosphereBackground()
            PanSlideLayout(panWidth: panWidth, revealed: revealed) {
                panContent()
                    .padding(.top, insets.top)
                    .padding(.bottom, insets.bottom)
                    .clipped()
                    .contentShape(Rectangle())
                    .allowsHitTesting(revealed > PanChrome.interactiveAfter)
                    .accessibilityHidden(revealed < PanChrome.accessibleAfter)
                content()
                    .overlay {
                        PanDim(
                            progress: progress,
                            revealed: revealed,
                            onClose: { pan.close() },
                            onDragChanged: { pan.drag = $0 },
                            onDragEnded: { pan.endDrag(predicted: $0, width: panWidth) }
                        )
                    }
                    .modifier(PanLidCard(progress: progress, radius: radius))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .clipped()
        .ignoresSafeArea()
        .animation(PanChrome.spring, value: pan.isOpen)
        .environment(\.panWidth, panWidth)
        .onKeyboardPresence { pan.keyboardUp = $0 }
    }
}

private enum PanChrome {
    static let dim = 0.2
    static let shadow = 0.22
    static let shadowRadius: CGFloat = 28
    static let shadowX: CGFloat = -6
    static let interactiveAfter: CGFloat = 8
    static let accessibleAfter: CGFloat = 12
    static let spring = Animation.spring(response: 0.38, dampingFraction: 0.86)
}

/// Flatten chrome so clip + shadow apply to the whole lid, including the bar.
private struct PanLidCard: ViewModifier {
    var progress: CGFloat
    var radius: CGFloat

    func body(content: Content) -> some View {
        let card = RoundedRectangle(cornerRadius: radius, style: .continuous)
        content
            .compositingGroup()
            .clipShape(card)
            .shadow(
                color: .black.opacity(PanChrome.shadow * progress),
                radius: PanChrome.shadowRadius,
                x: PanChrome.shadowX,
                y: 0
            )
    }
}

private struct PanDim: View {
    var progress: CGFloat
    var revealed: CGFloat
    var onClose: () -> Void
    var onDragChanged: (CGFloat) -> Void
    var onDragEnded: (CGFloat) -> Void

    var body: some View {
        Color.black.opacity(PanChrome.dim * Double(progress))
            .allowsHitTesting(revealed > PanChrome.interactiveAfter)
            .onTapGesture(perform: onClose)
            .gesture(closeDrag)
            .accessibilityLabel("Закрыть сковородку")
            .accessibilityAddTraits(.isButton)
            .accessibilityHidden(revealed < PanChrome.interactiveAfter)
    }

    private var closeDrag: some Gesture {
        DragGesture(minimumDistance: 8, coordinateSpace: .global)
            .onChanged { value in
                guard abs(value.translation.width) >= abs(value.translation.height) else { return }
                onDragChanged(value.translation.width)
            }
            .onEnded { value in
                onDragEnded(value.predictedEndTranslation.width)
            }
    }
}

private extension View {
    func onKeyboardPresence(_ change: @escaping (Bool) -> Void) -> some View {
        onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillShowNotification)) { _ in
            change(true)
        }
        .onReceive(NotificationCenter.default.publisher(for: UIResponder.keyboardWillHideNotification)) { _ in
            change(false)
        }
    }
}
