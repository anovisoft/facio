# Execution Engine

## Purpose

Run the project after plan creation with **no LLM in the happy path**.

Responsibilities:

- materialize schedules from PlanGraph + calendar constraints
- present next action
- record completion / skip / evidence
- compute progress & stage unlocks
- detect stalls
- apply deterministic adaptations & playbooks
- emit telemetry

## Mental model

```text
PlanGraph (what) + Scheduler (when) + State Machine (status) + Evaluators (progress/success)
```

## PlanGraph runtime

Nodes kinds (extensible enum):

- `practice` — do a skill drill
- `habit` — recurring behavior
- `chore` — shopping, setup
- `milestone_check` — evaluate success fragment
- `learning` — short educational card (keep rare)
- `rest` — planned recovery
- `review` — weekly structured review

Edges / unlocks:

- stage completion thresholds
- time gates (min days)
- metric gates (e.g., can hold dead hang 30s)
- manual coach unlock (exceptional)

## Scheduler

Inputs:

- days_per_week / available windows
- action dose durations
- timezone
- blackout dates
- recovery rules

Outputs:

- Action instances with due windows

### Scheduling policies

- **strict**: fixed weekdays
- **flexible**: N sessions/week anytime
- **deadline-backplan**: rare; use carefully (anxiety)

Prefer flexible with gentle nudges for most life goals.

## Next Action selector

Priority:

1. overdue primary actions
2. today’s primary
3. quick wins if user is stalled (shrink-next-action)
4. reviews due
5. optional bonus nodes (never block)

UI shows **one** primary. Lists are secondary.

## Progress model

Avoid fake percentages when outcome is skill-based.

Better:

- stage index
- consistency (completed / scheduled)
- leading indicators (hang time, weekly deficit, pages written)
- confidence in evidence

“62% to pull-up” is often a lie. Prefer “Stage 2/4 · 5 sessions this week target 3.”

## Stall detection engine

Deterministic detectors:

| Signal | Example rule |
|--------|--------------|
| consecutive misses | ≥3 primary actions missed |
| week completion | <30% scheduled in a week |
| silence | no open / complete events in N days |
| explicit | user taps “I’m struggling” |
| oscillation | skip pattern on same node type |

Outputs: `stall_score`, `probable_cause_candidates`, recommended playbook.

## Adaptation engine

Patch operations (examples):

- `SHIFT_DATES`
- `REDUCE_VOLUME`
- `SWAP_NODE`
- `INSERT_DELOAD_WEEK`
- `PAUSE_UNTIL`
- `CONVERT_TO_MINIMAL_PLAN`
- `ADVANCE_STAGE` / `REGRESS_STAGE`

All patches versioned; user-visible diff.

## Playbook executor

Playbooks are parameterized scripts:

```text
illness_deload_v1:
  if horizon allows:
    insert deload week
    shift remaining
    message: short explanation
  else:
    offer pause or pivot
```

No generative text required; use localized string templates with variables.

## Offline & sync

- local action queue
- conflict rule: server authoritative for schedule mutations; client authoritative for completion timestamps within skew window
- idempotent event ids

## Why this is the real product

Anyone can generate a plan. Few products **operate** a plan through missed Tuesdays, travel, and shame spirals.

If engineering effort disproportionately goes to chat UX instead of this engine, Facio will not differentiate.

## Critique: “AI almost never used” 

Correct target for *token spend*. Incorrect if interpreted as “plans never change.”

Plans change constantly. The win is **changes without tokens**.
