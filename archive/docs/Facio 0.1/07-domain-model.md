# 07 — Domain model

Target mental model for Facio 0.1. Implementation may keep legacy table names temporarily — semantics should match this.

---

## Entity graph

```text
User
  └── Guide[]          (was: Project)
        ├── Cover        emoji/mark, difficulty, duration summary
        ├── Identity     started_at, progress, streak, counts
        ├── Contract     result, success_criteria, horizon (finite end)
        ├── Cycle[]      index, horizon_days, status, anchor, result
        │     └── Session[]   atoms: one opening → complete
        │           └── UIBlock[]
        └── state versions / audit  (Undo + Repair Diff)
```

Plus product system (not necessarily a table): **Focus Engine** ranks ready Sessions for Continue.

User-facing focus: **Guide** (Cover + Identity + roadmap) and **Session** (Execute + complete beat).

---

## Guide

| Field (conceptual) | Notes |
|--------------------|-------|
| id | |
| status | draft/proposal → active → completed / archived / abandoned |
| cover | emoji/mark, accent?, difficulty, duration_summary |
| title, summary | narrative |
| result / outcome | what you get |
| success_criteria | **finite** contract — Guide must be able to end |
| paraphrase | soft understanding of Intent |
| identity | started_at, progress, streak, completed/repaired/skipped counts |
| cycles | history + current |
| committed_at | Commitment moment |
| progress | derived (also on Identity) |

Invariant: before leaving proposal/draft toward active, user has been able to see roadmap (Commitment).  
Invariant: completion goes through **Finish Experience**, not silent status only.

## Cover

| Field | Notes |
|-------|-------|
| mark | emoji or visual token |
| difficulty | e.g. Easy |
| duration_summary | e.g. 25 min / 14 days / 3 sessions |
| accent? | optional color for lists |

Generated at create; editable. Used on Continue, drawer, Guide header.

## Identity

| Field | Notes |
|-------|-------|
| started_at | Commitment date |
| progress_to_outcome | 0–1 or bar toward success |
| streak | define carefully (consecutive Session completes) |
| sessions_completed | |
| sessions_repaired | count of repair events affecting path |
| sessions_skipped | |

Derived + stored counters OK. Surface on Guide; thin slice on Continue optional.

## Cycle

| Field | Notes |
|-------|-------|
| index | 1..N within Guide |
| horizon_days | e.g. 1 (cook) / 7 (training) |
| status | active / completed / abandoned |
| goal_for_cycle? | optional |
| days / schedule | map for roadmap + unlock |
| cycle_result | structured, for next cycle |
| cycle_anchor_date | physical day unlock |

## Session

Executable unit for Continue + Session screen. **Atom of execution.**

| Field | Notes |
|-------|-------|
| id | |
| guide_id, cycle_id | |
| day_index / schedule slot | when multi-day |
| title | |
| status | pending / ready / in_progress / done / skipped / locked / incomplete |
| ui_blocks | closed enum payloads |
| support copy | short title / now line; detail optional |
| estimated_min? | helps Focus Engine + Cover |

**Atomicity:** designed to finish in **one opening**. Happy path is not multi-day resume of the same Session — incomplete → repair/reschedule/replace. Short same-day crash resume may exist; see [11 §3](./11-success-systems.md).

**Note:** Prototype modeled “day + actions + plugins”. Facio 0.1 treats **Session** as the product unit — one Continue card, one Execute screen, one Session complete beat.

## UI Block

Closed client enum. LLM fills schema; client renders.

Seed from prototype: `checklist`, `timer_stack`, `timeline`, `interval_plan`, `stepper`, `counter`.  
Extend deliberately (flashcards, reading, …) only with client support.

Rules carried forward:

- Timeline XOR timers on one cook axis
- Strength approaches → stepper beats, not checklist rows
- Hints on Guide roadmap; live payloads at Execute as needed

## Focus Engine

Deterministic ranker over ready Sessions → ordered Continue + Focus.  
Inputs: overdue, last day, priority, time-of-day fit, short duration, streak risk, etc.  
No LLM required for daily ranking. See [11 §1](./11-success-systems.md).

## Clarify

Batch `questions[]` + optional `comment` per refine round.

## Repair

Product operations mutating the living Guide (shift / lighten / rest / domain-specific + reason).  
**Required:** Diff preview → apply. **Required:** Undo via state_versions. Audited.

## Commitment

Not necessarily a separate table — a transition: Guide `proposal` → `active`, anchor set, Identity.started_at, first Session unlocked per physical-day rules.

## Finish Experience

Product flow (screen/sheet) when Guide success criteria met: celebration + Identity stats + Repeat / Start next Guide. Not only a status enum.

---

## Physical day (keep)

Program day ≠ click-through entire Cycle in one evening.

- `unlocked_day_index` from local today − cycle anchor  
- Execute only unlocked (catch-up OK)  
- Future Sessions visible on Guide, not executable  

Horizon=1 Guides behave as single-Session flows.

---

## Audit (keep)

Preserve prototype audit maximalism: turns, llm_calls, state_versions, events. Needed for learning and dogfood debug.

---

## Instant Answer

Not a core entity in 0.1. Do not invest in gate `instant_answer` as a product peer. Prefer always steering toward a Guide, or a soft decline + Create again.
