import SwiftUI

struct DeedsList: View {
    @Environment(DeskStore.self) private var store
    var onOpen: (String) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Практики")
                .font(.headline)
                .foregroundStyle(.primary)
            ForEach(store.snapshot.subjects) { subject in
                let live = liveWidget(subject.id)
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
                                now: Date(),
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

    private func liveWidget(_ subjectId: String) -> Widget? {
        let all = store.snapshot.widgets.filter { $0.subjectId == subjectId && $0.type.showsOnLid }
        if let today = all.first(where: { $0.section == .today && $0.status != .done }) { return today }
        if let done = all.first(where: { InstanceLaw.isDoneToday($0, now: Date()) }) { return done }
        return all.first
    }
}
