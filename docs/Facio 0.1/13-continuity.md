# 13 — Continuity (do not lose after chat summary)

Working memory across sessions. Product canon = `01`–`11`. Process = [12](./12-process.md). Slices = [14](./14-impl-plan.md).

**Update this file** when a slice is accepted, a landmine is found, or PO decides an open question.

---

## Snapshot (2026-08-03)

| Layer | State |
|-------|--------|
| Product vector | Facio 0.1 locked (Continue / Guide / Session + success systems) |
| Prototype engine | `apps/` ≈ `docs/next` slices 1–5 **accepted** |
| Carbonara dogfood | OK (timeline → finish → Repeat) |
| Fitness multi-day E2E | Deferred — needs calendar week or **dev time travel** |
| Facio 0.1 code shell | **Not started** — docs only |
| Instant Answer | Demote/remove in 0.1 happy path |

---

## Fragile knowledge (summary will drop this — keep here)

### Doc pack roles

| Path | Role |
|------|------|
| `docs/Facio 0.1/` | **Source of truth** for UX/IA/terms/success systems |
| `docs/next/` | How runtime was built; grammar splits; physical day; stepper |
| `docs/mvp/` | Frozen first experiment |
| `docs/RFC/` | Long-horizon Outcome OS — do not override 0.1 UX |

Conflict → **Facio 0.1 wins** on surface; keep next engine.

### Anthropic structured output landmine

- Error: `400 grammar too large` on constrained JSON schema  
- **Sonnet does not fix it** — same grammar limit as Haiku  
- Create is **3-phase**: `#1` gate/start → `#2` Path + `plugin_hints` (no plugin objects) → `#3` materialize plugins after Start  
- Do not merge full PathState + InstantAnswer + plugins into one schema  
- Failed `#2`/`#3` must still commit audit (`llm_calls` / error turns)  
- Detail: `docs/next/09-continuity.md` (Anthropic section)

### Physical day

- Execute only `day_index ≤ unlocked_day_index`  
- Future days preview OK, controls disabled  
- Closing day N early must **not** unlock N+1 same calendar day  
- Repair must respect unlock  

### Session Stage (already in code spirit)

- Block hero ~2/3; burger → full plan  
- Wire plugin name **`stepper`** (not `set_plan`); beats `measure|work|rest`  
- Strength: one session action / day; no checklist-as-sets  

### Mapping prototype → 0.1 (code names still old)

| Code today | Product 0.1 |
|------------|-------------|
| `Project` | Guide |
| `ProjectsScreen` | → Continue + drawer |
| `ProjectHomeScreen` | → Session |
| `PathScreen` | → Guide roadmap |
| `DraftStudioScreen` | → Guide Explore |
| `InstantAnswerScreen` | → cut from happy path |
| plugins | UI Blocks |
| `state_versions` | Undo foundation |

Prefer **aliases / new screens** over big-bang DB rename.

### Success systems that must not be “later polish”

From [11](./11-success-systems.md): Focus Engine, Session complete beat, Session atom, finite Guide, Repair Diff, Undo, Cover, Identity, Finish Experience.

---

## Open PO decisions (block silent invention)

| ID | Question | Default until PO speaks |
|----|----------|-------------------------|
| D1 | Focus Engine weights / pin Focus? | Deterministic v0: overdue > last day > short ≤5m > others; no pin |
| D2 | Incomplete Session resume window? | Same calendar day only; else incomplete → reschedule/repair path |
| D3 | Streak definition? | Consecutive calendar days with ≥1 Session complete on Guide |
| D4 | Commitment separate route? | Sticky CTA on Guide (no separate route) |
| D5 | Instant Answer? | Remove from happy path (hide or delete) |
| D6 | `project`→`guide` rename when? | After shell works; aliases first |
| D7 | Cover generation? | LLM fills emoji+difficulty+duration_summary on create #1/#2 |
| D8 | Finish vs Next Cycle confusion in UI? | Next Cycle = chapter; Finish = Guide success criteria met |

---

## Slice status

| Slice | Name | Status |
|-------|------|--------|
| A | IA shell (nav: Continue / Session / Guide / Create / drawer) | **in progress** |
| B | Focus Engine v0 + Cover on cards | pending |
| C | Guide Explore trust (roadmap + Commitment; fold Draft) | pending |
| D | Session atom + Session complete beat + swipe/≡ | pending |
| E | Repair Diff + Undo | pending |
| F | Identity + Finish Experience | pending |
| G | Copy/i18n + kill Instant Answer + Morning Summary | pending |
| H | (optional) time travel for fitness dogfood | pending |

---

## Engineering pointers (apps)

- Client: `apps/mobapp-rn` — Expo RN, nav in `src/navigation/`  
- API: `apps/backend-py3/client-service` — FastAPI, Alembic through `011`  
- Auth: `X-Device-Id`  
- Docker: postgres `:5435`, backend `:8000`  

Do not start Facio 0.1 by rewriting the backend runtime. Shell first.

---

## After summarization — PM start here

1. Read [README](./README.md) → [11](./11-success-systems.md) → this file → [14](./14-impl-plan.md)  
2. Confirm with PO: start Slice A?  
3. Dispatch subagent with Slice A brief from [14](./14-impl-plan.md)  
4. Update this status table when done
