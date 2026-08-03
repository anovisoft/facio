# 06 — UX flows

Canonical flows for Facio 0.1.

---

## A. First Guide (Create → Explore → Commit → Execute)

```text
Continue (empty or +)
  → Create: “What do you want?”
  → AI understands Intent
  → Clarify (batch questions + optional free-text) while Guide appears
  → Guide screen (Explore): result, duration, success, roadmap
       user may edit / re-clarify
  → Commitment: Start Guide
  → Guide active
  → First Session ready on Continue
  → Open Session → UI Blocks → Done
  → Leave app
```

**Rules:**

- Never force Start without a readable full path (roadmap).
- Do not require a second full-map Accept screen.
- Progressive generation OK: slim sense → full roadmap → materialize live Blocks at Session start if needed for latency/schema limits.
- No chat-home during this flow; operations under the hood OK.

---

## B. Daily return (Execute)

```text
Open app
  → (optional) Morning Summary if warranted (Focus-aligned)
  → Continue: Focus Engine order (Focus card first)
  → Tap Session
  → Execute UI Blocks in one opening
  → Session complete beat
  → Continue (next Focus) or leave app
```

User should not need to read news, browse all Guides, or talk to AI.
Session should not be “half-done for two days” — see [11 §3](./11-success-systems.md).

---

## C. Open Guide from Session (orientation)

```text
Session
  → swipe up or ≡
  → Guide roadmap (progress, upcoming, past Sessions)
  → swipe down / back
  → Session
```

Use when: “how much left?”, “what’s next week?”, repair context, motivation/trust dip.

---

## D. Multi-Guide

```text
Continue shows Sessions from all active Guides
Drawer lists all Guides
New Create does not auto-archive others
```

Focus among many Guides: Continue order by readiness / today’s focus (soft). No forced single-active.

---

## E. Repair

```text
From Session or Guide
  → Something changed? / Repair Guide
  → Choose intent (+ reason / comment)
  → Diff screen (before → after) — required
  → Confirm
  → Apply + Undo available
  → Updated Guide + current Session / Continue
```

Repair respects physical/calendar unlock where Cycles are multi-day (prototype rule: cannot execute future days early).

Domain-aware intents over time (fitness ≠ one-shot cook).
Never silent magic rewrite.

---

## F. End of Cycle → next

```text
Cycle complete (or early finish with partial result)
  → Structured cycle result
  → CTA: Next Cycle / Repeat (e.g. cook)
  → Optional batch clarify
  → New Cycle on same Guide + new Sessions
```

Gesture is deterministic — not “ask the AI to continue” as the only path. Copy hints from model OK.

---

## G. Complete Guide / Finish Experience

```text
Last Session → Session complete beat
  → Guide success criteria met (finite end)
  → Finish Experience
       You did it · stats (days, Sessions, repairs, skipped)
       [ Repeat ]  [ Start next Guide ]
  → Removed from Continue
  → Archive / drawer (with Cover)
```

Do **not** only flip `status=completed`.  
Domain continuation (English A1 → A2) = **new Guide**, not infinite same Guide.  
See [11 §4 + §8](./11-success-systems.md).

Mid-Guide chapter end remains **Next Cycle** (flow F) — different from Guide Finish.

---

## Clarify UX (on Guide)

- Batch questions on one surface + always-available comment (“anything else”).
- Do not: one question → full LLM wait → next question as the only loop.
- Answers should not wipe when roadmap finishes loading (preserve by question id set).

---

## Copy orientation

Primary CTAs:

| Moment | Example CTA |
|--------|-------------|
| Commitment | Start Guide |
| Continue Focus card | Continue / Start Session |
| Session end | Session complete → Continue |
| Cycle end | Next Cycle / Repeat |
| Guide end | Finish Experience → Repeat / Start next Guide |
| Drift | Repair Guide (via Diff) |
| After mutation | Undo |

Avoid as primary product nouns: Project, Accept path, Ask AI.

---

## Anti-flows (do not ship)

1. Blank prompt home as the only surface  
2. Hide roadmap until after Start  
3. Duplicate full map on Accept after already showing Guide  
4. Instant Answer as equal peer to Guide creation  
5. Chat thread as daily driver  
6. Home = list of Guides/projects without ready Sessions  
7. Session body = entire plan essay with tiny plugin at the bottom  
8. Prolong Cycle only via freeform chat  
9. Swipe-to-Guide with **no** visible affordance  
10. Continue sorted only by `updated_at` / creation (no Focus Engine)  
11. Silent Done with no Session complete beat  
12. Multi-day resume of the same Session as happy path  
13. Infinite Guide with no Finish Experience  
14. Repair/AI Edit without Diff or without Undo
