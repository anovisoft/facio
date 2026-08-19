import SwiftUI

struct UseScreen: View {
    let widgetId: String
    @Environment(DeskStore.self) private var store
    @Environment(TalkStore.self) private var talk

    var body: some View {
        Group {
            if let widget = store.widget(id: widgetId) {
                content(for: widget)
                    .navigationTitle(DisplayCopy.title(subjectId: widget.subjectId, stored: widget.title))
                    .modifier(UseDateSubtitle(dateLabel: quietDate(store.snapshot.instances.first { $0.id == widget.instanceId }?.when)))
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
        case .checklist, .timer, .stepper:
            ContentUnavailableView {
                Text("Этот тип ещё не открывается.")
            }
        }
    }

    private func quietDate(_ date: Date?) -> String {
        (date ?? Date.now).formatted(.dateTime.day().month(.wide).locale(Locale(identifier: "ru_RU")))
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
