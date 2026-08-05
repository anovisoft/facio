# 15 — Edit surfaces (Plan Feed · Manual · Micro)

Canonical model for **building** and **rebuilding** a Guide (PO lock 2026-08-05).  
Complements [05](./05-screens.md), [06](./06-ux-flows.md), [11 §5–6](./11-success-systems.md).

---

## One insight

Create and Repair share a **propose** engine. UX differs by lifecycle:

| Phase | Surfaces |
|-------|----------|
| **Create / Explore** (pre-Commitment) | **Plan Feed** (AI) + **Manual** (all UI Block tools) |
| **Active** (post-Commitment) | **Manual** + **Micro-edits** (deterministic) + **AI Feed** (repair) |

Do **not** collapse these into one button soup on Session. Session stays Execute-only; edit opens these surfaces.

Chat-home remains forbidden ([02 P6](./02-principles.md)). Feed lives only inside Create / Edit — closed item types; answers are **plans and questions**, not open chat.

---

## Three mechanics (never merge)

### 1. Plan Feed / AI Feed

Lenta like a chat, but system turns are:

- short sense
- **plan cards** (versioned; expandable roadmap + tools)
- clarifying **questions**
- optional system notes

**Rules:**

- New AI revision = **new card below** — never overwrite a previous plan card in place.
- After user answers, AI may emit a new plan card **or** only more questions (no plan change).
- Bottom of feed: free-form input always available.
- Closed item set: `user_*`, `sense`, `plan_card`, `questions`, `system_note`.

**Create:** each `plan_card` has its own CTA (**Start Guide** / Use this plan). **No sticky page-bottom CTA.**

**Active AI Feed:** choosing a proposal → **Diff required** → confirm → apply → **Undo** (`state_versions`). Intents (shift / lighten / rest) seed the feed as chips — not Session chrome.

### 2. Manual editor

First-class on **both** Create and Active. Without Manual, Create is not usable (PO).

User can edit **all UI Block tools** on the plan/session:

- Checklist — add / remove / edit items  
- Stepper / Counter — targets, sets, labels  
- Other closed Block types — same editable fields Full Block exposes (not raw JSON)

Shared component Create ↔ Active. Inventing new Block *types* stays AI. Manual mutates the selected plan version (Create) or living Guide/Session (Active) with Undo.

### 3. Micro-edits (Active only)

Deterministic, **not** inside the Feed:

- Skip Session  
- Postpone / move day  
- Similar one-tap structure nudges

Live in Session kebab / Guide chrome. No LLM. Fast life adjustments.

---

## Entry points

| From | Opens |
|------|--------|
| Create after Intent | Plan Feed (Explore) |
| Plan card on Create | Manual on that version; CTA Start on card |
| Session kebab → Edit Session | Manual (Session scope) + entry to AI Feed / full Guide |
| Guide → Edit plan | Manual (Guide scope) + AI Feed |
| Session kebab micro | Skip / Postpone — stay chrome, not Feed |

Repair / lighten / rest **off** Session happy path (chrome lock).

---

## Trust policy

| Change | Trust |
|--------|--------|
| Create — pick plan card | CTA on that card → Commitment |
| Create — Manual on a card | Mutates that version; same card CTA |
| Active — AI proposal apply | **Diff** → confirm → Undo |
| Active — Manual structural / load | Prefer Diff; tiny field tweaks → apply + Undo toast |
| Active — Micro-edit | Deterministic apply; Undo where versioned |

---

## Shared pipeline (engine)

```text
propose(intent | free-text | clarify_answers)
  → proposed_state | follow_up_questions | diff_lines
apply(proposed_state, before_version) → undo_version
manual_patch(tools / structure) → version
micro_edit(skip | postpone | …) → deterministic API
```

Reuse Slice E `repair/preview` + Diff + Undo; progressive create `#1/#2/#3` unchanged. Do not expand Anthropic grammar.

---

## Implementation slices (see [14](./14-impl-plan.md))

After E (+ Session chrome) accept:

1. **E2a — Create Plan Feed** (лента + CTA on cards; Manual can stub)  
2. **E2b — Manual editor** (all tools; Create + Active)  
3. **E2c — Active AI Feed** + Diff on apply  

Then **F** Identity + Finish.

Micro-edits: extend existing kebab APIs; do not redesign into Feed.
