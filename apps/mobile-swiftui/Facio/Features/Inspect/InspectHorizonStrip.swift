import SwiftUI

struct InspectHorizonStrip: View {
    let days: [DayStrip]
    let subjectId: String
    let selectedId: String
    var onSelectInstance: (String) -> Void

    var body: some View {
        HStack(spacing: 6) {
            ForEach(days) { strip in
                InspectHorizonCell(
                    strip: strip,
                    subjectId: subjectId,
                    selectedId: selectedId,
                    onSelectInstance: onSelectInstance
                )
            }
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Неделя")
    }
}

private struct InspectHorizonCell: View {
    let strip: DayStrip
    let subjectId: String
    let selectedId: String
    var onSelectInstance: (String) -> Void

    var body: some View {
        let owned = strip.slots.filter { $0.subjectId == subjectId }
        let instanceId = tapTarget(in: owned)
        let selected = instanceId == selectedId
        let kind = cellKind(owned)
        Group {
            if let instanceId {
                Button {
                    onSelectInstance(instanceId)
                } label: {
                    InspectHorizonDayLabel(date: strip.date, kind: kind, selected: selected)
                }
                .buttonStyle(.plain)
                .accessibilityAddTraits(selected ? .isSelected : [])
            } else {
                InspectHorizonDayLabel(date: strip.date, kind: kind, selected: false)
            }
        }
        .frame(maxWidth: .infinity)
        .accessibilityLabel(accessibilityName(date: strip.date, kind: kind))
    }

    private func tapTarget(in owned: [Slot]) -> String? {
        let real = owned.compactMap(\.instanceId)
        if real.contains(selectedId) { return selectedId }
        return real.first
    }

    private func cellKind(_ owned: [Slot]) -> InspectHorizonKind {
        if owned.contains(where: { $0.kind == .due }) { return .due }
        if owned.contains(where: { $0.kind == .done }) { return .done }
        return .empty
    }

    private func accessibilityName(date: Date, kind: InspectHorizonKind) -> String {
        let stamp = DisplayCopy.loudDate(date)
        switch kind {
        case .due:
            return String(localized: "\(stamp), к делу", comment: "Inspect horizon due day")
        case .done:
            return String(localized: "\(stamp), готово", comment: "Inspect horizon done day")
        case .empty:
            return String(localized: "\(stamp), пусто", comment: "Inspect horizon empty day")
        }
    }
}

private enum InspectHorizonKind {
    case due
    case done
    case empty
}

private struct InspectHorizonDayLabel: View {
    let date: Date
    let kind: InspectHorizonKind
    let selected: Bool

    var body: some View {
        VStack(spacing: 2) {
            Text(weekday)
                .font(.caption2)
            Text(dayNumber)
                .font(.headline)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .foregroundStyle(foreground)
        .background(fill, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
    }

    private var weekday: String {
        date.formatted(.dateTime.weekday(.abbreviated).locale(Locale(identifier: "ru_RU")))
    }

    private var dayNumber: String {
        date.formatted(.dateTime.day().locale(Locale(identifier: "en_US_POSIX")))
    }

    private var foreground: Color {
        switch kind {
        case .due: Color.primary
        case .done: Color.secondary
        case .empty: Color.secondary.opacity(0.45)
        }
    }

    private var fill: Color {
        if selected { return Color.primary.opacity(0.12) }
        switch kind {
        case .due: return Color.primary.opacity(0.06)
        case .done: return Color.primary.opacity(0.04)
        case .empty: return Color.clear
        }
    }
}
