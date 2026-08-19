import SwiftUI

struct PanGutter: View {
    @Environment(PanSession.self) private var pan
    @Environment(\.panWidth) private var panWidth

    var body: some View {
        if pan.gutterEnabled {
            Color.clear
                .frame(width: FacioPalette.panGutter)
                .frame(maxHeight: .infinity)
                .contentShape(Rectangle())
                .gesture(openDrag)
                .accessibilityHidden(true)
        }
    }

    private var openDrag: some Gesture {
        DragGesture(minimumDistance: 10, coordinateSpace: .global)
            .onChanged { value in
                guard abs(value.translation.width) > abs(value.translation.height) else { return }
                pan.drag = max(0, value.translation.width)
            }
            .onEnded { value in
                pan.endDrag(
                    translation: value.translation.width,
                    predicted: value.predictedEndTranslation.width,
                    width: panWidth
                )
            }
    }
}
