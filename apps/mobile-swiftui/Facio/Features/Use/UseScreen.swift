import SwiftUI

struct UseScreen: View {
    let widgetId: String
    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk
    @State private var helpOpen = false

    var body: some View {
        Group {
            if let widget = store.widget(id: widgetId) {
                content(for: widget)
                    .navigationTitle(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                    .modifier(UseDateSubtitle(dateLabel: dateLabel(for: widget)))
                    // The `?` lives in the bar, not in the step body: the
                    // capsule (− / + / Готово), the system bar and the swipe
                    // back are the accepted Use layout and nothing here moves
                    // them. It appears only when this practice actually has an
                    // explanation to give.
                    .toolbar {
                        if store.hasExplanation(for: widget) {
                            ToolbarItem(placement: .topBarTrailing) {
                                Button {
                                    store.markExplanationsSurfaced(widgetId: widget.id)
                                    helpOpen = true
                                } label: {
                                    Image(systemName: "questionmark.circle")
                                }
                                .accessibilityLabel("объяснение")
                            }
                        }
                    }
                    .sheet(isPresented: $helpOpen) {
                        StepHelpSheet(cues: store.explanations(for: widget))
                    }
            } else {
                ContentUnavailableView {
                    Text("Этого виджета уже нет на крышке.")
                }
                .navigationTitle("Facio")
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .toolbarTitleDisplayMode(.large)
        .facioChrome()
        .facioComposerDock()
        .onAppear { talk.focusedWidgetId = widgetId }
        .onDisappear {
            if talk.focusedWidgetId == widgetId {
                talk.focusedWidgetId = nil
            }
        }
    }

    @ViewBuilder
    private func content(for widget: Widget) -> some View {
        if store.subject(id: widget.subjectId)?.status == .paused {
            PausedUseView()
        } else {
            let cue = store.surfaceCue(for: widget)
            switch widget.type {
            case .counter:
                CounterUseView(widget: widget, cue: store.cueFor(subjectId: widget.subjectId))
            case .tick:
                TickUseView(
                    widget: widget,
                    onToggle: { store.toggleTick(widgetId: widget.id) }
                )
            case .reminder:
                ReminderUseView(widget: widget, cue: cue)
            case .checklist:
                ChecklistUseView(widget: widget, cue: store.cueFor(subjectId: widget.subjectId))
            case .timer:
                TimerUseView(widget: widget, cue: store.cueFor(subjectId: widget.subjectId))
            case .stepper:
                StepperUseView(widget: widget, cue: store.cueFor(subjectId: widget.subjectId))
            }
        }
    }

    private func dateLabel(for widget: Widget) -> String {
        if store.subject(id: widget.subjectId)?.status == .paused {
            return DisplayCopy.pausedNow
        }
        return quietDate(store.snapshot.instances.first { $0.id == widget.instanceId }?.when)
    }

    private func quietDate(_ date: Date?) -> String {
        (date ?? Date.now).formatted(.dateTime.day().month(.wide))
    }
}

private struct PausedUseView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(DisplayCopy.pausedNow)
                .font(.title3.weight(.semibold))
                .foregroundStyle(.primary)
            Text("Сегодня этого нет.")
                .font(.body)
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal, FacioPalette.pagePadding)
        .padding(.top, 8)
    }
}

private struct UseDateSubtitle: ViewModifier {
    let dateLabel: String

    func body(content: Content) -> some View {
        if #available(iOS 26, *) {
            content.navigationSubtitle(dateLabel)
        } else {
            content
        }
    }
}
