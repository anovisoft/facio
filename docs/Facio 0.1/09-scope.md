# 09 — Scope

Scope for the Facio 0.1 **implementation wave** (product shell + IA over existing engine).

---

## One-liner

> Reposition the working cycle/plugins engine into Continue + Guide (Explore/trust) + Session (Execute), with Commitment after a visible roadmap — without rebuilding the runtime from scratch.

---

## Must have

### Product / UX

- Continue as app home with **Focus Engine** ranking (not `updated_at`)
- Guide page: **Cover** + result + finite success + roadmap + **Identity** + Start Guide
- Full path visible **before** Commitment
- Session screen: UI Blocks hero + **Session complete** beat; affordance to Guide (swipe + ≡)
- Session **atomicity**: one-opening design (no multi-day resume happy path)
- Create: *What do you want?* → clarify → Guide Explore → Commitment
- Guides drawer with Covers (+ archive + settings entry)
- Repair with **Diff** + **Undo**; AI Edit same
- Guide **finite end** + **Finish Experience** (not silent completed)
- Multi-active Guides
- No chat-home
- No Instant Answer as primary peer flow

### Engine (already largely present — preserve)

- Cycles + schedule + physical day unlock
- UI Blocks: checklist, timers, timeline, interval, stepper, counter
- Progressive create / materialize blocks
- Batch clarify + comment
- Next cycle / repeat CTA (mid-Guide chapters)
- Audit + state_versions (foundation for Undo)

### Success systems

Lock rules in [11](./11-success-systems.md) before heavy UI code. Especially: Focus Engine, atomic Session, Diff+Undo, Finish Experience.

### Quality bars

- Carbonara-class one-Session Guide (timeline) + Finish beat
- Push-ups-class multi-day Guide (stepper + cycle) — dogfood when calendar/time-travel allows

---

## Should have

- Morning Summary (Focus-aligned)
- Floating pencil edit hub (manual / AI edit / repair / structure)
- Richer Guide roadmap visuals (journey, not list)
- Domain-aware Repair intents + free-text reason in UI
- Focus reason chips on Continue (*Overdue*, *5 min*, …)
- Tunable Focus weights / user pin Focus
- Compact sticky Block bar on Session scroll (prototype should-have)

---

## Out of scope (this wave)

- Blueprint DSL / VectorDB / hybrid retrieval (RFC later)
- AI Coach billing product
- Monetization / App Store as success criterion
- Marketplace / Intent Economy
- Freeform LLM UI widget constructor
- Medical / clinical domains
- Equal quality for arbitrary intents without wedge discipline
- Full DB rename big-bang (`projects` → `guides`) unless cheap aliases
- Social / accountability network

---

## Explicit non-regressions

Do not ship 0.1 if:

- User can Start Guide without seeing a roadmap
- Home returns to Guides/projects list as the only root
- Continue order is unexplained / arbitrary
- Session is again a text booklet with tiny plugin
- Session complete has no victory beat
- Guide ends with silent `completed` only
- Repair/AI Edit applies without Diff or Undo
- Instant Answer is the happy path for “I want…”
- Daily Session completion requires an LLM call

---

## Success for this wave (dogfood)

Internal users:

1. Create a Guide and **understand the path before Start** (Cover + roadmap)
2. Trust Continue Focus order (“this is the right card”)
3. Live Continue → Session → **Session complete** → leave
4. Open Guide for Identity / orientation when needed
5. Repair with visible Diff + Undo if needed
6. Finish a Guide and feel the **Finish Experience**
7. Prefer this over “ask ChatGPT for a plan again”
