# 02 — Principles

Binding product rules for Facio 0.1. Use these to accept or reject feature proposals.

---

## P1 — Execution first

Optimize for:

- Commitment (Guide becomes active)
- Action (Session done)
- Continuity (returns next day)
- Completion (outcome criteria met)

Do **not** optimize for message volume, chat fluency, or “plans generated”.

## P2 — Guide / Continue / Session (core split)

> **Guide determines the path.** (*Where am I going?*)  
> **Continue determines the focus.** (*What matters now?*)  
> **Session ensures execution.** (*How do I do it?*)

| Need | Surface |
|------|---------|
| Evaluate the path, volume, trust before starting | **Guide** (page) |
| Browse / switch which paths I am on | **Guides drawer** (compact inventory) |
| See ready work that needs attention **now** | **Continue** (home — Hero Preview stack) |
| Perform the next executable unit | **Session** (Full Block) |

**Placement rule:** if you cannot decide where new info goes — ask which question it answers. If none, it probably does not belong.

**Do not twin Continue and Guides drawer** with the same Guide-Cover cards. Drawer = navigation rows; Continue = Session workspace.

## P3 — Explore Mode vs Execute Mode

Natural human split:

### Explore (before Commitment, and whenever trust is needed)

User studies the Guide: full path, duration, difficulty, cycles, edits.  
Question: *“Where am I going?”*

### Execute (after Commitment)

User mostly lives in Sessions. Guide stays available but is not the daily home.  
Question: *“What do I do now?”*

**Rule:** the user decides when to switch from understand → do. Never force “just start” without a visible path.

## P4 — Full path before start is mandatory

Hiding the route until after Start is a UX error.

Most people will **not** begin a Guide they cannot see.

Trust requirements before Commitment:

- what the result is
- how long / how many Sessions or Cycles
- what success means
- the shape of the first Cycle / path map

Trust ≠ shipping every live UI Block before Start. Readable **roadmap** is required; live timers may materialize at Session start (see progressive create in migration).

## P5 — Home is Continue, not Guide list

Home shows **ready Sessions** across active Guides.

Guide does **not** disappear — it stops being the homepage.

Projects drawer / Guides list is secondary navigation.

## P6 — AI is infrastructure, not surface

AI is used for:

- understanding Intent
- clarifying questions
- generating Guide
- Repair / AI edit of Guide

AI is **not**:

- home screen
- primary navigation
- open-ended chat product

Under the hood, operations may call LLM; the visible product is Guide + Session + Continue.

**Allowed exception — Plan Feed / AI Feed** (see [15](./15-edit-surfaces.md)): inside Create Explore and Active Edit only, a closed **лента** may look chat-like, but turns are **plan cards, questions, sense** — not a daily chat product. No chat-home. Manual edit of UI Block tools is first-class alongside the feed; micro-edits (skip / postpone) stay deterministic chrome.

## P7 — Session must be maximally executable

A Session is not a paragraph of advice.

It is a unit with **UI Blocks** (timer, stepper, timeline, checklist, flashcards, …) that make “doing” obvious.

Differentiation vs todo lists lives here.

## P8 — Repair is first-class

Life will break the plan. Repair must be fast and visible — not buried on Session Execute chrome.

Active rebuild uses three independent mechanics ([15](./15-edit-surfaces.md)): **Manual**, **Micro-edits**, **AI Feed** (Diff before apply). Same living Guide — not a separate chat world.

## P9 — Short navigation

Three levels only:

```text
Continue → Session → Guide
```

(+ Create as entry to a new Guide; Guides drawer as index)

No deep project trees as the daily experience.

## P10 — Determinism in the daily loop

After plugins/UI Blocks exist for a Session, completing them should not require an LLM call.

LLM for create / clarify / repair / edit / next-cycle.  
Daily Session runtime: client + deterministic API.

## P11 — One living Guide

No mandatory duplicate “draft map then accept map again”.

One Guide surface that evolves: clarify → commit → repair → next cycle.

Commitment is the **contract to start**, not the first time the path is shown.

## P12 — Vision test

For any feature:

1. Does it increase probability of finishing the Guide?
2. Does it reduce time-to-first-Session after Intent?
3. Does it keep Explore and Execute psychologically separate?
4. Would it still matter if LLMs were free and perfect tomorrow?

If (4) is only “more AI chat”, reject.

## P13 — Focus Engine owns Continue order

Continue order is a product decision, not `updated_at`.  
Focus Engine answers: *If only one card — which?*  
Details: [11 §1](./11-success-systems.md).

## P14 — Session is an atom with a victory beat

- Designed for **one opening** → complete → leave  
- End with **Session complete** feeling, not a silent Done  
- Multi-day goals = many Sessions, not one lingering Session  

## P15 — Guides are finite stories

Every Guide has an end → **Finish Experience**.  
Domain continues as a **new Guide** (e.g. English A1 → A2), not `Guide ∞`.

## P16 — Mutations are visible and reversible

Repair / AI Edit: always show **Diff**, then apply.  
Always offer **Undo** (state version). No magic silent rewrites.

## P17 — Cover + Identity

Guide has an emotional **Cover** and an **Identity** surface (started, streak, counts, progress).  
Session stays Execute; Identity lives on Guide.
