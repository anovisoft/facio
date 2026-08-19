import SwiftUI

struct InspectScreen: View {
    let subjectId: String
    let instanceId: String

    @Environment(DeskStore.self) private var store
    @State private var selectedId = ""

    var body: some View {
        let instances = store.instances(for: subjectId)
        let selected = instances.first { $0.id == selectedId } ?? instances.first { $0.id == instanceId }
        VStack(alignment: .leading, spacing: 20) {
            if let selected {
                Text(DisplayCopy.loudDate(selected.when))
                    .font(.largeTitle.weight(.bold))
                    .foregroundStyle(.primary)
                    .fixedSize(horizontal: false, vertical: true)
                Text(DisplayCopy.instanceStatus(selected.status))
                    .font(.title3)
                    .foregroundStyle(.secondary)
            }
            InstanceStrip(instances: instances, selectedId: $selectedId, onAdd: add)
            if let selected {
                InspectBody(
                    instance: selected,
                    widget: store.widget(instanceId: selected.id),
                    cue: store.cueFor(subjectId: subjectId),
                    window: store.windowFor(subjectId: subjectId)
                )
            }
            Spacer(minLength: 0)
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .navigationTitle(DisplayCopy.title(subjectId: subjectId, stored: store.subject(id: subjectId)?.title ?? subjectId))
        .toolbarTitleDisplayMode(.inline)
        .facioChrome()
        .onAppear {
            selectedId = instanceId
        }
        .onChange(of: instances.map(\.id)) { _, ids in
            if !ids.contains(selectedId) {
                selectedId = ids.last ?? instanceId
            }
        }
    }

    private func add() {
        if let created = store.addInstance(subjectId: subjectId) {
            selectedId = created
        }
    }
}

private struct InspectBody: View {
    let instance: Instance
    let widget: Widget?
    let cue: Cue?
    let window: TimeWindow?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let widget {
                switch widget.type {
                case .counter:
                    Text("\(widget.counterCount) / \(widget.counterTarget)")
                        .font(.system(size: 44, weight: .bold, design: .rounded))
                        .foregroundStyle(.primary)
                    if let cue {
                        Text(cue.text)
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(.primary)
                    }
                case .tick:
                    HStack(spacing: 12) {
                        Image(systemName: widget.isTickDone ? "checkmark.circle.fill" : "circle")
                            .font(.system(size: 44))
                            .foregroundStyle(widget.isTickDone ? .primary : .secondary)
                            .accessibilityHidden(true)
                        Text(widget.isTickDone ? "готово" : "на Сегодня")
                            .font(.title3)
                            .foregroundStyle(.secondary)
                    }
                case .reminder:
                    if let window {
                        Text(DisplayCopy.succeedBy(window))
                            .font(.title3.weight(.semibold))
                            .foregroundStyle(.primary)
                    }
                    if let cue {
                        Text(cue.text)
                            .font(.body)
                            .foregroundStyle(.secondary)
                    }
                case .checklist, .timer, .stepper:
                    EmptyView()
                }
            }
        }
        .accessibilityElement(children: .combine)
    }
}
