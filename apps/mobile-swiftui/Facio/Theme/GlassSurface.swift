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
    var action: (() -> Void)?
    @ViewBuilder var content: () -> Content

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous)
        let chrome = content()
            .padding(16)
            .frame(minWidth: 0, maxWidth: .infinity, minHeight: 0, maxHeight: .infinity, alignment: .topLeading)
            .contentShape(shape)
            .facioGlass(dimmed: dimmed)
        Group {
            if let action {
                Button(action: action) { chrome }
                    .buttonStyle(.plain)
            } else {
                chrome
            }
        }
        .frame(minWidth: 0, maxWidth: .infinity, minHeight: 0, maxHeight: .infinity)
        .clipShape(shape)
    }
}

struct FacioGlassButton: ViewModifier {
    var prominent: Bool
    var capsule: Bool = false

    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            if prominent {
                content.buttonStyle(.glassProminent)
            } else {
                content.buttonStyle(.glass)
            }
        } else if capsule {
            content
                .buttonStyle(.borderedProminent)
                .buttonBorderShape(.capsule)
        } else {
            content
                .buttonStyle(.bordered)
                .buttonBorderShape(.roundedRectangle)
        }
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

    func facioGlassButton(prominent: Bool, capsule: Bool = false) -> some View {
        modifier(FacioGlassButton(prominent: prominent, capsule: capsule))
    }
}
