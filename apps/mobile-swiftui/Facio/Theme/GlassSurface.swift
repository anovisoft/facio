import SwiftUI

struct FacioGlassCluster<Content: View>: View {
    var spacing: CGFloat = FacioPalette.gridGap
    @ViewBuilder var content: () -> Content

    var body: some View {
        if #available(iOS 26, *) {
            GlassEffectContainer(spacing: spacing) {
                content()
            }
        } else {
            content()
        }
    }
}

struct FacioTileButton<Content: View>: View {
    var dimmed: Bool = false
    let action: () -> Void
    @ViewBuilder var content: () -> Content

    var body: some View {
        Button(action: action) {
            content()
                .padding(16)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .contentShape(RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous))
                .facioGlass(dimmed: dimmed)
        }
        .buttonStyle(.plain)
    }
}

extension View {
    @ViewBuilder
    func facioGlass(dimmed: Bool = false, interactive: Bool = true) -> some View {
        let shape = RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous)
        if #available(iOS 26, *) {
            if dimmed {
                glassEffect(.regular.tint(Color.primary.opacity(0.06)), in: shape)
                    .opacity(0.78)
            } else if interactive {
                glassEffect(.regular.interactive(), in: shape)
            } else {
                glassEffect(.regular, in: shape)
            }
        } else {
            background(.ultraThinMaterial, in: shape)
                .opacity(dimmed ? 0.75 : 1)
        }
    }

    @ViewBuilder
    func facioCircleGlass(interactive: Bool = true) -> some View {
        if #available(iOS 26, *) {
            glassEffect(interactive ? .regular.interactive() : .regular, in: .circle)
        } else {
            background(.ultraThinMaterial, in: Circle())
        }
    }
}
