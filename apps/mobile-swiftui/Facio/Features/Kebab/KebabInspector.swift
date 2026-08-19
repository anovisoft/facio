import SwiftUI

struct KebabInspector: View {
    let subjectId: String
    var onInspect: (String, String) -> Void
    var onTalk: (String?) -> Void

    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @State private var selectedId = ""

    var body: some View {
        let instances = store.instances(for: subjectId)
        let title = DisplayCopy.title(
            subjectId: subjectId,
            stored: store.subject(id: subjectId)?.title ?? subjectId
        )
        VStack(alignment: .leading, spacing: 20) {
            Text(title)
                .font(.title2.weight(.semibold))
                .foregroundStyle(.primary)
            InstanceStrip(instances: instances, selectedId: $selectedId, onAdd: add)
            Button {
                onInspect(subjectId, selectedId)
            } label: {
                Text("Открыть")
                    .font(.headline)
                    .frame(maxWidth: .infinity, minHeight: 52)
            }
            .disabled(selectedId.isEmpty)
            .facioGlassButton(prominent: true, capsule: true)
            talkMiniature
            Spacer(minLength: 0)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 20)
        .padding(.bottom, 16)
        .onAppear(perform: pickDefault)
        .onChange(of: instances.map(\.id)) { _, ids in
            if selectedId.isEmpty || !ids.contains(selectedId) {
                selectedId = ids.last ?? ""
            }
        }
    }

    @ViewBuilder
    private var talkMiniature: some View {
        let binding = talk.lastBinding(subjectId: subjectId)
        Button {
            onTalk(binding?.thread.id)
        } label: {
            VStack(alignment: .leading, spacing: 8) {
                Text("Разговор")
                    .font(.caption.weight(.medium))
                    .foregroundStyle(.secondary)
                if let snapshot = binding?.snapshot {
                    Text(DisplayCopy.title(subjectId: snapshot.subjectId, stored: snapshot.title))
                        .font(.headline)
                        .foregroundStyle(.primary)
                    Text(snapshot.line)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                        .fixedSize(horizontal: false, vertical: true)
                } else {
                    Text("ещё не начинался")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .contentShape(RoundedRectangle(cornerRadius: FacioPalette.tileRadius, style: .continuous))
            .facioGlass()
        }
        .buttonStyle(.plain)
        .accessibilityLabel("Разговор")
    }

    private func pickDefault() {
        if selectedId.isEmpty {
            selectedId = store.preferredInstanceId(subjectId: subjectId) ?? ""
        }
    }

    private func add() {
        if let created = store.addInstance(subjectId: subjectId) {
            selectedId = created
        }
    }
}
