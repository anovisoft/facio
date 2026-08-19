import SwiftUI

struct DeedsList: View {
    @Environment(DeskStore.self) private var store
    var onOpen: (String) -> Void

    var body: some View {
        let now = Date()
        VStack(alignment: .leading, spacing: 10) {
            Text("Практики")
                .font(.headline)
                .foregroundStyle(.primary)
            ForEach(store.snapshot.subjects) { subject in
                let live = InstanceLaw.preferredLive(
                    in: store.snapshot.widgets,
                    subjectId: subject.id,
                    now: now
                )
                Button {
                    onOpen(subject.id)
                } label: {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(DisplayCopy.title(subjectId: subject.id, stored: subject.title))
                            .font(.headline)
                            .foregroundStyle(subject.status == .retired ? .secondary : .primary)
                        Text(DisplayCopy.cadence(subject.cadence))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(
                            DisplayCopy.holding(
                                subject: subject,
                                instances: store.snapshot.instances,
                                now: now,
                                liveSection: live?.section,
                                liveStatus: live?.status
                            )
                        )
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)
                .accessibilityLabel(DisplayCopy.title(subjectId: subject.id, stored: subject.title))
            }
        }
    }
}
