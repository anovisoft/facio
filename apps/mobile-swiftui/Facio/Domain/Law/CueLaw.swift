import Foundation

enum CueLaw {
    static func defaultSurface(for kind: CueKind) -> CueSurface {
        switch kind {
        case .correction: .doTime
        case .clarification: .onDemand
        }
    }

    static func addCue(
        id: String,
        subjectId: String,
        kind: CueKind,
        text: String,
        surface: CueSurface? = nil,
        stepId: String? = nil,
        quote: String? = nil,
        media: CueMedia? = nil,
        origin: CueOrigin? = nil,
        hits: CueHits = CueHits()
    ) -> Cue {
        Cue(
            id: id,
            subjectId: subjectId,
            stepId: stepId,
            kind: kind,
            text: text,
            quote: quote,
            media: media,
            origin: origin,
            surface: surface ?? defaultSurface(for: kind),
            hits: hits
        )
    }

    static func doTimeCue(in cues: [Cue], subjectId: String) -> Cue? {
        cues.last { $0.subjectId == subjectId && $0.surface == .doTime }
    }

    static func timingCue(in cues: [Cue], subjectId: String) -> Cue? {
        cues.last { $0.subjectId == subjectId && $0.surface == .timing }
    }

    static func surfaceCue(in cues: [Cue], subjectId: String, widgetType: WidgetType) -> Cue? {
        switch widgetType {
        case .reminder:
            timingCue(in: cues, subjectId: subjectId)
        case .counter, .tick, .checklist, .timer, .stepper:
            doTimeCue(in: cues, subjectId: subjectId)
        }
    }
}
