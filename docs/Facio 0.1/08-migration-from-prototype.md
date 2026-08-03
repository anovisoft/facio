# 08 — Migration from prototype

Big-brush map from current `apps/` + `docs/next` → Facio 0.1.  
Detail tickets belong in implementation plans; this is the product→code vector.

---

## Verdict

**Keep the execution engine. Re-skin the product shell around Continue / Guide / Session.**

Do not rewrite FastAPI + RN from scratch. Do not throw away cycles, plugins, physical day, repair, next-cycle, progressive create, audit.

---

## Keep (engine)

| Capability | Notes |
|------------|-------|
| Cycle + schedule days + kinds | Roadmap + unlock |
| Physical day unlock | Multi-day integrity |
| Plugins runtime | → UI Blocks |
| Progressive create #1/#2/#3 | Latency / Anthropic grammar |
| Batch clarify + comment | On Guide Explore |
| Repair + versioned state | First-class surface → Diff + Undo |
| Next cycle / repeat | Mid-Guide chapters; Guide end → Finish Experience |
| Multi-active | Multi-Guide + Focus Engine |
| Audit trail / state_versions | Keep — Undo foundation |
| Session Stage layout spirit | Hero Block on Session + complete beat |
| Carbonara + push-ups quality bars | Dogfood continue |
| First Completion energy | Generalize to every Session complete |
---

## Rename / reframe (product language)

| Prototype | Facio 0.1 |
|-----------|-----------|
| Project | Guide |
| Path / Plan / Draft studio | Guide (Explore) |
| Accept / Save & start | Commitment / Start Guide |
| Project Home «Сегодня» | Session |
| Plugins | UI Blocks |
| Projects root list | Continue (+ Guides drawer) |
| PathScreen list | Guide roadmap |

DB/API identifiers may migrate gradually; **UI and agent docs use 0.1 terms.** Prefer additive API fields / aliases over big-bang renames mid-flight.

---

## Rebuild / major UX change

### 1. Root navigation → Continue + Focus Engine

Replace Projects-as-home with Focus-ranked Session cards across Guides.  
Focus Engine is new product logic (deterministic); do not ship unsorted lists.

### 2. Elevate Guide page

PathScreen-style list → **Cover** + **Identity** + beautiful roadmap + contract (finite end) + Commitment CTA.  
Peer to Session, not a buried burger dump.

### 3. Session as dedicated Execute screen

ProjectHome becomes Session-focused; leave multi-Guide overview to Continue.  
Add **Session complete** beat; enforce **one-opening** atom policy.

### 4. Create → Guide Explore → Commitment

DraftStudio collapses into Guide Explore; Commitment is Start Guide on that surface (no Accept duplicate).  
Generate **Cover** at create.

### 5. Session ↔ Guide gesture

Swipe up/down + visible ≡ affordance.

### 6. Edit pencil surface + Diff + Undo

Manual / AI Edit / Repair / structure — visible.  
Always Diff before apply; Undo via existing `state_versions`.

### 7. Finish Experience

New end-of-Guide flow (celebration + stats + Repeat / Next). Distinct from mid-Guide next-cycle.

### 8. Morning Summary

New optional surface; must use same Focus Engine as Continue.

---

## Cut or demote

| Item | Action |
|------|--------|
| Instant Answer product branch | Remove or hide; conflicts with “does not answer questions” |
| Chat-home experiments | Stay forbidden |
| Accept full-map duplicate | Already deprecated in next — keep dead |
| “Why now” booklet competing with Block hero | Keep support text short; don’t revive booklet home |
| Marketing “any intent at equal quality” | Keep wedge quality bar |

---

## Soft conflicts resolved

| Tension | Resolution |
|---------|------------|
| Continue-only home vs need full plan | Guide page mandatory before Start; always reachable |
| Session-first vs Explore | Two modes; user switches |
| Progressive plugins vs trust | Roadmap before Start; live Blocks at Session OK |
| Swipe discoverability | Swipe + explicit control |
| Many ready Sessions | Focus Engine picks Focus; others ranked |
| Crash mid-Session | Short same-opening resume OK; not multi-day happy path |

---

## Suggested implementation waves (orienting)

Not a rigid sprint plan — order of risk:

1. **IA shell** — Continue root, Guides drawer, Session route, Guide route, wiring  
2. **Focus Engine v0** + Cover fields on cards  
3. **Guide trust UI** — Cover + Identity + roadmap + Commitment; fold DraftStudio  
4. **Session polish** — Block hero + Session complete beat + swipe/≡ + atom policy  
5. **Diff + Undo** on Repair/AI Edit; Finish Experience  
6. **Copy + i18n + kill Instant Answer**; Morning Summary  
7. **Optional:** API/DB rename aliases `project→guide` when stable  

Fitness multi-day dogfood (time travel) remains useful engineering — orthogonal to IA, still valuable.

---

## Docs relationship after this pack

- Implementers read **`docs/Facio 0.1/`** first  
- `docs/next/` = how the current engine was built (reference)  
- `docs/mvp/` = frozen experiment  
- `docs/RFC/` = long-horizon; do not override 0.1 UX/IA without product decision
