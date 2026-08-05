# 14 — Implementation plan (slices)

Ordered slices for Facio 0.1 shell over existing engine.  
PO may reorder. PM dispatches **one slice** at a time. Status lives in [13](./13-continuity.md).

Canon: [11](./11-success-systems.md). Process: [12](./12-process.md).

---

## Slice A — IA shell

**Goal:** App opens on Continue; can open Session, Guide, Create, Guides drawer — wired to existing project data (even if ugly).

**DoD:**

- Root ≠ Projects list; root = Continue (may temporarily list one Session per active project)
- Routes/screens exist: Continue, Session, Guide, Create, drawer
- Existing ProjectHome / Path / Intent logic reachable through new names or wrappers
- Instant Answer not linked from Create happy path (can leave dead code)
- No Focus Engine polish required yet (stable but naive order OK if documented)

**Non-goals:** Cover polish, Finish Experience, Diff UI, roadmap beauty.

**Likely touch:** `apps/mobapp-rn/src/navigation/*`, `features/projects/*`, new `features/continue/*` or rename, thin wrappers.

**PO dogfood:** Open app → see Continue → open a Session → open Guide → Create field visible from `+`.

---

## Slice B — Focus Engine v0 + Cover

**Goal:** Continue order is intentional; cards feel like Guides (Cover glance).

**DoD:**

- Named Focus Engine module (client and/or API) with documented v0 rules (see D1 default in [13](./13-continuity.md))
- First card = Focus; optional reason chip for top signals
- Cover fields on Guide (emoji/mark, difficulty, duration_summary) — persist + show on Continue/drawer
- Generate Cover on create (or sensible fallback from title/domain)

**Non-goals:** Perfect weights, user pin, Morning Summary.

**PO dogfood:** Two+ active Guides → top card reason makes sense; Cover fields persist (Guide surfaces / data).

---

## Slice B2 — Hero Preview + drawer compact

**Goal:** Continue and Guides drawer stop twinning; Continue becomes a living workspace.

**DoD:**

- Guides drawer = **compact navigation** (emoji/mark + title [+ thin status]); no large Cover twin cards
- Continue cards = **Hero Preview** for current Session (read-only fragment of Block state — checklist rows / set progress / timer readout — not “Checklist · title” only)
- Continue shows only Sessions that **need attention** (executable / overdue); idle waiting Guides drawer-only
- Focus reason chip retained; Guide emoji may be a small context mark
- Hero Preview is **not** interactive Full Block (tap → Session)
- Document per-Block Hero contract in continue feature README (start with checklist + stepper + timeline/timer; others may fallback gracefully)

**Non-goals:** Interactive ☐ on Continue; Guide roadmap beauty (Slice C); Session complete beat (Slice D); perfect Hero for every Block type day one.

**PO dogfood:** Open drawer vs Continue — clearly different. Continue cards show action fragments; tap opens Full Block Session.

---

## Slice C — Guide Explore + Commitment

**Goal:** Trust before Start; DraftStudio folded into Guide.

**DoD:**

- Guide screen shows roadmap (not only PathList dump) + contract fields + Cover
- Pre-commit: Start Guide CTA on Guide; path visible
- Clarify/refine works on Guide Explore
- No Accept duplicate full map
- Progressive create `#1/#2/#3` preserved (do not break grammar split)

**Non-goals:** Identity full stats, Finish Experience.

**PO dogfood:** New Intent → see path → Start Guide → Session appears on Continue.

---

## Slice D — Session atom + complete beat + Guide gesture

**Goal:** Execute feels like a victory atom; Guide one gesture away.

**DoD:**

- Session complete beat (copy + visual) before returning to Continue
- Policy for incomplete: same-day resume only (D2 default); no multi-day resume happy path
- Swipe up and/or ≡ Session → Guide; back down/back
- Block hero retained (Session Stage spirit)

**Non-goals:** Pencil hub, Morning Summary.

**Carry from polishing bugs** (`docs/polishing bugs.txt` — PO 2026-08-03):

- Stepper **step back** (bug #2)
- Persist stepper / Session Block state across leave→return same day (bug #6) — aligns with D2
- Recompose Session layout (bug #7): title → day N/M (if multi-day) → large Full Block (bigger controls/icons) → description / “why today” lower (copy TBD)

**PO dogfood:** Finish carbonara Session → feel complete → land on Continue; leave mid-stepper → return same day → state kept; Session chrome matches Continue glass menu size.

---

## Slice E — Repair Diff + Undo

**Goal:** Mutations are visible and reversible.

**DoD:**

- Repair flow shows before→after Diff, then confirm
- Undo restores prior `state_versions` (or equivalent) after Repair/AI Edit
- No silent apply

**Non-goals:** Domain-specific cook repair intents (can keep shift/lighten/rest + reason).

**PO dogfood:** Repair → see Diff → apply → Undo works.

---

## Slice E2a — Create Plan Feed

**Goal:** Create Explore becomes a versioned лента (plans + questions), not in-place DraftStudio.

**DoD:**

- After Intent: feed with sense → plan card v1 → questions → answers/freeform → new plan card **or** more questions
- New AI revision appends below; prior cards remain
- Each plan card has **Start Guide** CTA; no sticky page-bottom Start
- Closed feed item types; not chat-home
- Progressive `#1/#2/#3` preserved

**Non-goals:** Full Manual on every Block type (E2b); Active AI Feed (E2c).

**PO dogfood:** Create carbonara → see v1 → answer questions → see v2 below → Start from preferred card.

Canon: [15](./15-edit-surfaces.md).

---

## Slice E2a-iterate — Create Plan Feed discoverability (#9)

**Goal:** External tester could not expand the plan and answered questions without pressing refine. Make Create feel stepped and obvious.

**DoD (from tester + PM):**

1. **Plan detail expanded by default** on every plan card (`PathList` visible; collapse optional, not required to discover).
2. **Stepped clarify:** when clarifying questions exist, present them as a clear step with primary CTA to refine **and** a secondary **«Build / update path without answers»** (empty answers + empty comment allowed) so refine is never a hidden requirement.
3. After a plan card is ready, questions sit **below** that plan (end of the step), not competing as the only visible surface while the plan looks “closed”.
4. i18n en/ru for the skip/build-without-answers control.
5. Preserve: append-only feed, Start CTA on card, MMKV history, Manual «Edit tools», progressive `#1/#2/#3`. Do not start Active AI Feed (E2c).

**Non-goals:** Server-side feed turns; Active pencil/Save-with-AI (#10 → E2c); inventing new Block types.

**PO dogfood:** Create Guide → see full plan without hunting expand → answer or skip questions → path updates → Start from card.

---

## Slice E2b — Manual editor (all UI Block tools)

**Goal:** Manual edit of checklist / stepper / counter / … on Create and Active.

**DoD:**

- Shared editor for closed Block tool fields (not raw JSON)
- Create: edit tools on a plan card version
- Active: Edit Session / Edit plan Manual mode → apply + Undo
- Inventing new Block types remains AI

**Non-goals:** Free-form plugin authoring; Active AI Feed UI (E2c).

**PO dogfood:** On Create, edit shopping checklist items before Start; on Active, change stepper targets without AI.

---

## Slice E2c — Active AI Feed + Diff

**Goal:** Repair-with-AI as a feed; apply via Diff (reuse Slice E).

**DoD:**

- Entry from Edit Session / Edit plan (not Session Execute chrome)
- Feed: intents / freeform / questions → proposal cards
- Apply → Diff → confirm → Undo
- Micro-edits (skip / postpone) stay kebab — not inside feed

**PO dogfood:** Lighten via AI Feed → Diff → apply → Block updates → Undo.

---

## Slice F — Identity + Finish Experience

**Goal:** Guide is my path; ending is a story.

**DoD:**

- Identity on Guide: started, progress, counts (streak per D3 default)
- Guide finite end triggers Finish Experience (stats + Repeat / Start next Guide)
- Distinct from Next Cycle mid-Guide
- Archive after celebration, not instead of it

**PO dogfood:** Complete short Guide (carbonara) → Finish Experience → Repeat or done.

---

## Slice G — Copy, Instant Answer kill, Morning Summary

**Goal:** Product language + cleanup.

**DoD:**

- i18n: Guide / Session / Continue / Start Guide / Session complete
- Instant Answer removed from happy path (D5)
- Morning Summary optional interstitial using Focus Engine

**PO dogfood:** No Instant Answer; copy matches 0.1; morning sheet if signal.

**Carry from polishing bugs:** #8 domain-neutral rest/day-kind copy (fitness phrases must not appear on cook/drawing/etc. Guides) — `path.restEmpty`, `dayKind.train`/`rest`, LLM day titles.

---

## Slice H — optional engine: time travel

**Goal:** Fitness multi-day dogfood without waiting a week.

**DoD:** Dev-only local date override for physical day unlock.

Only if PO prioritizes push-ups E2E over shell polish.

---

## Parallelism note

Default **serial** A→B→B2→C→D→E→E2a→E2b→E2c→F→G.  
Possible parallel later: H alongside shell if different owners; not with A.  
E2a/b/c canon: [15](./15-edit-surfaces.md). Compact Summary on Guide roadmap lands primarily in **C**; B2 owns Hero + drawer.

---

## Subagent brief template (PM fills)

```text
You are implementing Facio 0.1 Slice <X>.
Read: docs/Facio 0.1/README.md, 11-success-systems.md, 13-continuity.md, this slice in 14-impl-plan.md.
Also: docs/next/09-continuity.md for engine landmines if touching create/plugins/day unlock.
Repo: apps/mobapp-rn + apps/backend-py3/client-service as needed.
DoD: <paste>
Non-goals: <paste>
Do NOT invent answers to open decisions D1–D8; use continuity defaults.
Do NOT expand Anthropic schemas in ways that risk grammar 400.
When done: list files changed, how to dogfood, leftover risks.
```
