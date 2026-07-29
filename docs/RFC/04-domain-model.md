# Domain Model

## Design stance

Model the world as **projects that pursue outcomes**, not as chat threads that accumulate messages.

If your schema centers on `Conversation`, you will rebuild ChatGPT. If it centers on `Project` + `PlanGraph` + `Action`, you can still add chat as a peripheral.

## Core entities

### User

- identity, locale, timezone
- preference profile (notification windows, available days)
- constraint profile fragments (equipment, dietary, budget band) — reusable across projects
- subscription / entitlement state
- risk / policy flags

### Intention (ephemeral)

Raw capture before binding:

- text / audio transcript
- embedding
- candidate outcome types + scores
- session id

Intentions may expire if never committed.

### OutcomeType

Stable taxonomy node (not free text):

- id: `fitness.strength.pullup_first`
- title, description
- domain, subdomain
- success criteria templates
- policy class (`standard` | `sensitive` | `restricted`)
- default blueprint id(s)

**Critique:** Do not equate “user utterance” with OutcomeType. Utterances map *onto* OutcomeTypes.

### Blueprint

Versioned template for producing plans for an OutcomeType (or family).

See [Blueprint System](./06-blueprint-system.md).

### Project

User-owned instance:

| Field | Notes |
|-------|-------|
| `id` | |
| `user_id` | |
| `outcome_type_id` | |
| `blueprint_id` + `blueprint_version` | pinned at creation; migrations explicit |
| `status` | draft/active/paused/stalled/completed/abandoned/pivoted |
| `contract` | success criteria, horizon, constraints snapshot |
| `slots` | answered clarification values |
| `plan_graph_id` | current plan |
| `created_at` / `activated_at` / `completed_at` | |

Invariant: a Project always has a Contract before leaving `draft`.

### Contract

- success criteria (structured)
- time budget (minutes/week)
- horizon (target date or checkpoint schedule)
- constraints (equipment, injuries, budget, diet)
- evidence requirements
- safety acknowledgements

### PlanGraph

Directed graph (usually DAG) of stages/nodes:

- stages (phases)
- nodes (actions / milestones / gates)
- edges (prerequisites, unlock rules)
- scheduling annotations
- adaptation hooks

Plans are **data**, not prompt transcripts.

### Action (Task instance)

Scheduled unit of execution:

- node template id
- due window
- status: pending/done/skipped/failed/rescheduled
- evidence payload
- effort estimate
- coach-needed flag (rare)

### Evidence

Typed payload:

- `self_report`
- `numeric_metric` (weight, kg lifted, savings amount)
- `checklist`
- `media` (photo/video) — optional, privacy-sensitive
- `external_import` (HealthKit, bank CSV — later)

### Event (telemetry)

Append-only product events:

- plan_created, action_completed, stall_detected, repair_applied, coach_invoked, abandoned…

Events power flywheel analytics; they are not the source of truth for plan state (that’s transactional state).

### RepairPlaybook

Deterministic response templates for common failure modes:

- missed_week
- low_motivation
- illness
- travel
- plateau
- time_shortage

### CoachSession

Billable / rate-limited generative interaction bound to a Project:

- trigger reason
- context snapshot (plan + recent events + slots)
- proposed patches
- user acceptance
- cost attribution

## Relationships (simplified)

```text
User 1—* Project
OutcomeType 1—* Blueprint (versions)
Project 1—1 Contract
Project 1—* PlanGraph (versions; one current)
PlanGraph 1—* Action
Project 1—* CoachSession
Blueprint 1—* RepairPlaybook binding
```

## Lifecycle invariants

1. Cannot activate Project without Contract + initial PlanGraph.
2. Plan patches create a new PlanGraph version (or append-only patch log) — never silent mutation without history.
3. Completion requires success criteria evaluator = true (or explicit manual complete with reason).
4. Abandonment requires reason code (system may assign `unknown` after timeout, but track it).
5. CoachSession cannot mutate plan without producing a reviewable patch set.

## Why not model “Goal” as free text only?

Free-text goals:

- cannot aggregate learning
- cannot attach proven strategies
- cannot enforce safety policy cleanly
- cannot power retrieval quality

Free text is an **input modality**. Canonical storage is structured OutcomeType + Contract.

## Multi-project reality

Users will run multiple projects. Early product should:

- allow multiple, but
- recommend **focus mode**: 1 primary project

Trying to be “life OS for 12 simultaneous transformations” is a retention killer.
