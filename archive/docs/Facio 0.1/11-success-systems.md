# 11 — Success systems (lock before heavy code)

Eight product systems that determine whether Facio feels like a **guide**, not a plan list — plus **Session presentations** (§9) that keep Continue / Guide / Session visually distinct.  
Treat as **canonical**. Do not ship Continue/Guide/Session shell without a clear stance on each.

---

## 1. Focus Engine (heart of Continue)

Continue does not show an arbitrary list of ready Sessions.

**Focus Engine** ranks and orders Sessions. It answers:

> If we could show only **one** card — which Session is it?

That top Session is the **Focus**. Everything else is secondary.

### Why order matters

```text
Carbonara
↑
Push-ups
↑
English
```

Without an explicit engine, order is accidental — and Continue fails its job.

### Inputs (v0.1 — deterministic rules first)

Rank with a transparent, explainable score. Suggested signals (weights tunable; LLM not required for daily ranking):

| Signal | Intent |
|--------|--------|
| Overdue / missed unlock | Urgent recovery |
| Last day of Cycle / Guide | Deadline pressure |
| User-set priority | Explicit preference |
| Time-of-day fit | e.g. usually mornings |
| Short Session (e.g. ≤5 min) | Low friction win |
| Streak / continuity risk | Keep momentum |
| Recency / last opened Guide | Soft continuity |

### Outputs

- Ordered Continue list  
- Single **Focus** Session (hero / first card)  
- Optional short reason chip: *Last day* / *Overdue* / *5 min* (trust; not a lecture)

### Rules

- Focus Engine is a **named product component**, not “sort by updated_at”.  
- Ranking must work offline / without LLM.  
- Morning Summary should align with Focus (same engine).  
- Soft focus among multi-Guide is **not** optional fluff — it is Continue’s core.

### Open (do not invent silently)

Exact weights and whether user can pin Focus — escalate if needed. Default: engine chooses; user can still tap any card.

---

## 2. Session completion feeling (small victory)

Session end is not a quiet checkbox.

**Required emotional beat:**

```text
Workout
█████████
Session complete
```

Not merely a button labeled *Done* that pops back to a list with no acknowledgment.

### Product bar

- Progress fills / resolves  
- Explicit **Session complete** (copy + visual)  
- Brief celebration (motion / mark) — calm, not casino  
- Then: return to Continue (next Focus) or close

Prototype “First Completion” energy belongs here for **every** Session, scaled down after the first.

### Placement

Belongs to **Session** (Execute), not Guide. Guide celebrates at **Finish Experience** (§8).

---

## 3. Session atomicity (one opening)

Session is an **atom** of execution.

Canonical loop:

```text
Open → Do → Complete → Leave → Next Session later
```

**Anti-pattern:**

```text
Open Session → abandon mid-way → return two days later → finish same Session
```

That turns Session into a lingering task and kills the atom.

### Rules

- A Session is designed to be **finished in one uninterrupted opening**.  
- Duration budget should fit that (minutes, not multi-day work disguised as one Session).  
- If the user leaves incomplete: prefer **incomplete → repair / reschedule / replace Session**, not “resume stale Session across days” as the happy path.  
- Multi-day goals are **many Sessions**, not one long Session.

### Edge cases (policy)

| Case | Direction |
|------|-----------|
| App crash mid-Session | May resume **same calendar opening / short window**; do not advertise multi-day resume |
| User hits Home mid-way | Incomplete; do not keep a half-done Session as Focus for days without Repair |
| Truly long work (cook 45m) | Still one opening; Session length OK if continuous |

If implementation needs a resume window (e.g. same day, &lt; N hours), document it — default product story remains **one opening**.

---

## 4. Guide must have an end

No infinite Guides as the default shape.

```text
English A1  →  Complete
English A2  →  new Guide
```

Not: `English ∞`.

### Rules

- Every Guide declares a **finite success / horizon** (Sessions count, days, skill gate, one dish, …).  
- Reaching the end triggers **Finish Experience** (§8), not a silent status flip.  
- Continuation of a life domain = **new Guide** (or explicit Next Guide suggestion), not an endless same object.  
- Cycles are internal chapters; they do not replace Guide completion.

### Why

Without an ending, achievement disappears and Facio collapses into a forever todo stream.

---

## 5. Repair is never magic — always show Diff

On an **active** Guide, AI proposals (AI Feed) and material structural mutations **must** show a human-readable Diff before apply. Create uses **Plan Feed** version cards instead of Diff ritual — pick CTA on the preferred card ([15](./15-edit-surfaces.md)).

Example:

```text
Repair
────────
Day 4  →  Day 6
Workout  →  Lighter workout
```

### Rules

- Active AI apply: confirm **before → after** for every material change.  
- No silent rewrite of the living Guide.  
- Diff is trust for rebuild; Create trust = visible plan cards + Manual.  
- Micro-edits (skip / postpone) are deterministic and outside the AI Feed.

---

## 6. Reversibility (Undo)

Mutations that change the Guide must be **undoable**.

Examples:

- Repair → Oops → **Undo**  
- AI Edit → wrong → **Undo**  
- Manual structure edit → **Undo**

### Rules

- Prefer restore previous **state version** (prototype already versions state).  
- Undo window: at least immediate post-action; longer history via version back is OK.  
- Undo itself should be obvious after Repair/AI Edit — not buried only in debug.  
- Completing a Session is a user action: undo-complete may exist as secondary; do not block Undo on Repair/Edit for lack of undo-complete.

---

## 7. Guide Cover (emotional identity card)

A Guide is not only text. It has a **Cover** — the emotional face for **Guide surfaces**: Guide page header, Archive, and a **thin** mark in the Guides drawer.

Example (Guide page / Archive):

```text
🍝  Carbonara
    Easy · 25 min · 3 sessions

🏋️  30 Push-ups
    14 days
```

### Cover fields (minimum)

| Field | Role |
|-------|------|
| Emoji / visual mark | Instant recognition |
| Title | Name of the path |
| Difficulty or effort | Trust / expectation |
| Duration summary | Sessions or days or minutes |
| Optional accent color | Living list, not gray rows |

**Continue does not use Cover as the card body.** Continue cards are **Hero Previews** of the current Session ([§9](#9-session-presentations-hero--full--compact)). Drawer stays compact (mark + title), not full Cover cards — otherwise Continue and Guides twin each other.

Roadmap remains for depth; Cover is the Guide glance layer.

---

## 8. Identity + Finish Experience

### 8a. Identity (missing entity — now first-class)

Above Cycle/Session bookkeeping, each active Guide carries **Identity**: the feeling that *this is my path*.

Not a social profile — a **per-Guide story surface**.

Example:

```text
30 Push-ups
██████░░░░
You started     3 Aug
Current streak  4
Sessions        12 completed
Repaired        2
```

| Identity signals | Notes |
|------------------|-------|
| Started at | Commitment date |
| Progress to outcome | Bar toward success criteria |
| Streak / continuity | Sessions in a row (define carefully) |
| Counts | completed / repaired / skipped |
| Cover | §7 |

**Placement:** lives on **Guide** (Explore / orientation). Continue may show a thin slice (Cover + Focus reason). Session stays Execute-only — Identity is not the Session hero.

### 8b. Finish Experience

When a Guide completes, do **not** only set `status=completed`.

Ship a dedicated **Finish Experience**:

```text
🎉 You did it.
30 push-ups.
14 days.
18 Sessions.
2 Repairs.
1 skipped.

[ Repeat ]     [ Start next Guide ]
```

### Rules

- Finish turns the Guide into a **finished story**, not a gray archive row.  
- Stats are honest (from Identity + cycle results).  
- CTAs: Repeat (same Guide shape / new instance) and/or Start next Guide (suggested or Create).  
- Archive comes after the beat — celebration first.

### Flow

```text
Last Session complete
  → (Session complete beat)
  → Guide success criteria met
  → Finish Experience
  → Repeat / Next / Archive
```

---

## 9. Session presentations (Hero / Full / Compact)

Same Session, **three contexts** — not one card reused everywhere. This is what separates Continue from Guides drawer and from Session execute.

| Name | Surface | Shows | Interactive (0.1) |
|------|---------|-------|-------------------|
| **Hero Preview** | Continue | Fragment of action (e.g. 3–5 checklist rows, set N/M + reps, timer readout) + ~duration + Focus chip | **No** — tap opens Session |
| **Full Block** | Session | Complete executable Block | **Yes** |
| **Compact Summary** | Guide roadmap | Title + status among many Sessions | No (tap → Session when allowed) |

### Why Hero Preview

Planner apps show labels (*Checklist · Buy groceries*). Facio shows a **slice of the real action** so the brain gets it in ~0.2s. That is “Guides you” on the home screen.

### Hard rules

- Hero Preview ≠ shrunk Full Block. Separate **read-only** view per Block type — avoid dual-execute implementations.  
- Making ☐ tappable on Continue later must not fork architecture — only flip interactivity on Hero.  
- Guides drawer stays **compact navigation** (inventory). Do not put Hero Previews or full Cover cards there.  
- Continue shows only Sessions that **need attention**; idle Guides live in the drawer.

### Naming (prefer over S/M/L)

Use **Hero Preview / Full Block / Compact Summary** in specs and code comments. Size letters confused “screen importance” with “object detail.”

---

## How these systems connect

```text
Focus Engine          → which Session now (Continue)
Hero Preview          → see the action on Continue (not a text label)
Full Block            → execute on Session
Compact Summary       → Session as a point on the Guide map
Atomic Session        → one opening → Session complete beat
Guide finite          → path has an end
Identity              → my path while active
Cover                 → Guide recognition (page / archive / thin drawer mark)
Repair Diff+Undo      → trust when life breaks the plan
Finish Experience     → story closes
```

If Continue and Guides drawer look the same, presentations failed. If Continue only shows “Checklist · …”, Hero Preview failed.

---

## Implementation priority (before lots of UI code)

| # | System | Lock in design/API early? |
|---|--------|---------------------------|
| 1 | Focus Engine | **Yes** — Continue is empty without it |
| 9 | Hero / Full / Compact | **Yes** — Continue vs drawer vs Guide must not twin |
| 3 | Session atomicity | **Yes** — affects Session model & resume policy |
| 4 | Guide finite end | **Yes** — contract / success criteria |
| 5–6 | Repair Diff + Undo | **Yes** — reuse state_versions |
| 2 | Session complete beat | UI must-have in Session slice |
| 7 | Cover | Schema + generate on create (Guide surfaces) |
| 8 | Identity + Finish | Guide model + end flow |

Weights and polish can iterate; **existence and rules** above are not optional for 0.1 success.
