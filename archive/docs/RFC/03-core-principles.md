# Core Principles

These are binding decision rules. If a feature violates them, it needs an explicit exception RFC.

## P1 — Outcome over conversation

Every surface must increase probability of outcome attainment or reduce time-to-next-action.

Chat that does not change project state is a leak.

## P2 — Deterministic core, generative edge

The execution path must run without LLM calls.

LLM is for:

- ambiguous intent interpretation
- residual personalization patches
- open-ended repair when rules fail
- rare content authoring (offline / admin)

## P3 — Minimum viable interrogation

Ask the fewest questions that materially change the plan.

If a question does not branch the blueprint or change load/safety, delete it.

## P4 — First action within 24 hours

A project that cannot propose a meaningful action within 24h of creation is broken (wrong blueprint grain or over-planning).

## P5 — Local repair before global replan

Prefer:

1. skip / swap today’s task
2. shift schedule
3. reduce intensity
4. branch strategy
5. full replan (expensive, disorienting)

## P6 — Evidence or it didn’t happen

Progress claims need an evidence model appropriate to the domain.

Self-report is allowed, but the system must know the confidence class of evidence.

## P7 — Cost is a product feature

Every generative call has a budget owner.

If a flow cannot state its expected tokens / call rate per MAU, it is not ready to ship.

## P8 — Safety is not a sidebar

Health, finance, legal, minors, self-harm adjacent intents require policy gates.

“Helpful plan” is not an excuse to give dangerous advice.

## P9 — Instrument failure causes

Abandonment without reason codes is wasted data.

Taxonomy of failure is a first-class product asset.

## P10 — Narrow excellence beats wide mediocrity

Do not expand taxonomy coverage until quality bars are met in current domains.

## P11 — User agency

Facio proposes; user owns.

No dark patterns that guilt-trip, no hostage streaks, no “you’ll lose your progress” manipulative copy as retention strategy.

## P12 — Explainability of adaptation

When the plan changes, show a human-readable reason:

- “You missed 3 sessions → week load reduced 30%”
- not “AI optimized your journey”

## Engineering correlates

| Principle | Engineering implication |
|-----------|-------------------------|
| P2 | Feature flags for LLM paths; offline-capable execution |
| P5 | Plan as versioned graph with patch operations |
| P6 | Evidence schema per blueprint |
| P7 | Per-route cost metrics in observability |
| P8 | Policy classifier before blueprint bind |
| P9 | Structured abandonment reasons + analytics events |

## Principle conflicts (acknowledge them)

- **Personalization vs cost:** more freeform personalization feels magical, burns margin.
- **Coverage vs quality:** “any goal” marketing fights P10.
- **Motivation vs agency:** coaching tone can tip into manipulation (violates P11).

Document the trade-off when you choose a side; do not pretend there is no conflict.
