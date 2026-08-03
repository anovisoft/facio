# Facio 0.1 — Product Source of Truth

> Status: **canonical product vector** for implementation  
> Audience: product, engineering, implementing agents  
> Replaces as day-to-day truth: [`../mvp/`](../mvp/README.md), [`../next/`](../next/README.md)  
> Long-horizon architecture (blueprints, retrieval, coach economics): still [`../RFC/`](../RFC/README.md) — subordinate to this pack on UX/IA/terminology

---

## What this is

This folder is the **single entry point** for building Facio after the prototype dogfood.

The prototype in `apps/` proved: intent → structured cycle → executable plugins → repair → next cycle.  
Facio 0.1 **repositions** that engine around **guiding**, not plan-browsing.

Older packs remain as history:

| Pack | Role now |
|------|----------|
| `RFC/` | Long-horizon Outcome OS architecture; keep for engines/cost/moat ideas |
| `mvp/` | First experiment (soft-start, Path, Today/Why) — frozen |
| `next/` | Accepted runtime stage (cycles, plugins, physical day, repair) — **engine to reuse**, UX/IA superseded |
| **`Facio 0.1/`** | Current product truth: positioning, IA, screens, migration |

---

## One-sentence product

> **Facio turns “I want…” into a Guide and leads the user to the result one Session at a time — with UI Blocks that make each Session executable.**

Slogan: **Guides you.**

Category line: **AI guide for anything you want to do.**

Not: AI planner, task manager, coach chat, habit tracker, ChatGPT for goals.

---

## Read order (agents: follow this)

1. [01 — Positioning](./01-positioning.md) — problem, promise, non-goals, wedge  
2. [02 — Principles](./02-principles.md) — Explore/Execute, Guide vs Session rule, AI role  
3. [03 — Terminology](./03-terminology.md) — Intent, Guide, Commitment, Cycle, Session, UI Block, Repair, Identity…  
4. [04 — Information architecture](./04-information-architecture.md) — three modes, navigation, Continue home  
5. [05 — Screens](./05-screens.md) — page inventory and jobs  
6. [06 — UX flows](./06-ux-flows.md) — create → commit → execute → repair → finish  
7. [07 — Domain model](./07-domain-model.md) — entity graph agents should target  
8. [08 — Migration from prototype](./08-migration-from-prototype.md) — what to keep / rename / cut / build  
9. [09 — Scope](./09-scope.md) — must / should / out for the 0.1 implementation wave  
10. [10 — Agent brief](./10-agent-brief.md) — decision checklist + anti-patterns for implementers  
11. [11 — Success systems](./11-success-systems.md) — **lock before heavy code**: Focus Engine, atomic Session, Cover, Identity, Finish…  
12. [12 — Process](./12-process.md) — PO / PM / subagent cadence  
13. [13 — Continuity](./13-continuity.md) — fragile memory after chat summary + slice status  
14. [14 — Impl plan](./14-impl-plan.md) — slices A→B→**B2**→C… with DoD  

---

## Product rule (memorize)

> **Guide determines the path.**  
> **Continue determines the focus.**  
> **Session ensures execution.**

Or by question:

> **Guide** — *Where am I going?*  
> **Continue** — *What matters now?*  
> **Session** — *How do I do it?*

Home (**Continue**) is the **workspace**: Focus-ranked Session **Hero Previews** (fragments of real action) — not a Guides inventory and not Full Block execute.

If a piece of UI/info helps **evaluate the path** → Guide.  
If it helps **perform the next step** → Session (Full Block).  
If it picks or ranks ready work across Guides → **Focus Engine / Continue** (Hero Preview).

Each UI Block must render in three **contexts** (see [11 §9](./11-success-systems.md)): Hero Preview / Full Block / Compact Summary.

**Before writing a lot of code:** read [11](./11-success-systems.md).  
**After chat summarization:** PM starts at [13](./13-continuity.md) + [14](./14-impl-plan.md).

---

## Three modes

```text
Create   →  “I want…”
Guide    →  “Show me the whole path.”   (Explore / trust)
Session  →  “Lead me now.”              (Execute)
```

Continue is the **execution home / attention stack**, not the project list.  
Guides drawer is **compact navigation** (inventory), not a second Continue.

---

## Stack (unchanged)

- Client: Expo / React Native (`apps/mobapp-rn`)
- API: FastAPI + Postgres (`apps/backend-py3/client-service`)
- LLM: structured generation on create / clarify / repair / edit / next-cycle only

---

## Naming

Product: **Facio**. Repo folder may stay `fasio`.  
In user-facing copy and new code comments prefer Facio 0.1 terms (Guide, Session, …).  
Internal DB/API may migrate gradually — see [08](./08-migration-from-prototype.md).
