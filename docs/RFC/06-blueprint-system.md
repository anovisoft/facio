# Blueprint System

## Why blueprints beat “generate a plan every time”

Generating plans from scratch:

- costs tokens every activation
- hallucinates unsafe progressions
- produces inconsistent structure (breaks execution engine)
- prevents aggregate learning (“which week-3 deload works?”)

Blueprints provide a **stable spine** that can be measured and improved.

## What a Blueprint is

A Blueprint is a versioned, declarative package:

```text
Blueprint
  metadata
  applicability (outcome types, constraint predicates)
  intake (questions / slots)
  contract templates
  plan skeleton (stages, nodes, unlock rules)
  scheduling rules
  adaptation rules
  repair playbook bindings
  evidence model
  content refs (exercises, recipes, scripts) — not walls of LLM prose
  evaluation (success criteria calculators)
```

Think **compiler intermediate representation for behavior change**, not a markdown essay.

## Blueprint grain (critical design choice)

Wrong grain examples:

- Too coarse: `Fitness.General` → useless personalization
- Too fine: `Fitness.WeightLoss.Female.Postpartum.Vegetarian.HomeOnly.BusyParent` as separate hard-coded blueprints → combinatorial explosion

### Recommended approach: Base + Mixins + Rules

```text
Base: Fitness.BodyComp.FatLoss.V1
  + mixin: equipment.home
  + mixin: diet.calorie_tracking.optional
  + rule: if days_per_week <= 2 → volume_profile.minimal
  + rule: if injury.knee → swap impact moves
```

Personalization becomes **feature composition**, not infinite named templates.

Named variants (`Beginner`, `Busy`) are OK as presets that set mixin bundles.

## Blueprint schema (conceptual)

```yaml
id: fitness.strength.pullup_first
version: 3
outcome_type: fitness.strength.pullup_first
policy_class: standard

applicability:
  experience: [none, beginner]
  equipment_any_of: [bar, band_bar]
  exclude_if:
    - injury.shoulder_acute

intake:
  - id: days_per_week
    type: enum
    values: [2, 3, 4]
    required: true
  - id: band_access
    type: boolean
    required: true
  - id: bodyweight_kg
    type: number
    required: false

contract:
  success:
    type: skill_check
    definition: unassisted_pullup_count >= 1
  default_horizon_weeks: 10

stages:
  - id: foundation
    unlock: always
    nodes:
      - id: scap_pulls
        kind: practice
        dose: { sets: 3, reps: 8 }
        schedule: { session_index: 1 }
  - id: assisted
    unlock: { after_stage: foundation, min_completion_rate: 0.8 }
    nodes: [...]

adaptations:
  - on: missed_sessions >= 3 in 7d
    do: apply_playbook missed_week_v2
  - on: rpe_avg >= 9 for 2 sessions
    do: reduce_volume_pct 20

repairs:
  illness: playbook.illness_deload_v1
  travel: playbook.travel_minimal_v1
  motivation: playbook.motivation_shrink_next_action_v1

evidence:
  action_default: self_report_sets
  milestone: optional_video
```

## Authoring workflow

1. Domain expert drafts structure (not an LLM “invent a program”).
2. Encode as schema; validate.
3. Simulate against synthetic personas.
4. Shadow test with internal users.
5. Publish version; pin for new projects.
6. Observe completion / stall / abandon metrics.
7. Patch rules; bump version.

LLM may assist authoring drafts **offline**. Runtime should not invent new blueprints for users in v1.

## Cold start strategy (this will make or break you)

You cannot wait for the flywheel to create quality.

### Phase 0 content

Hand-build 20–40 excellent blueprints in the wedge domains.

Quality bar per blueprint:

- [ ] clear success criteria
- [ ] ≤5 intake questions
- [ ] Day-1 action exists
- [ ] at least 3 repair playbooks bound
- [ ] safety notes reviewed
- [ ] estimated time/week honest
- [ ] can execute fully without LLM

### User-defined goals outside library

Options (pick deliberately):

| Option | Pros | Cons |
|--------|------|------|
| A. Soft reject + suggest nearest | Quality control | Feels limited |
| B. Generic “custom project” scaffold | Coverage | Becomes todo app; weak outcomes |
| C. LLM-generated ephemeral blueprint | Magic | Cost, safety, no learning |
| D. Waitlist / contribute request | Focus | Friction |

**Recommendation:** A for MVP, with B as limited escape hatch that is clearly second-class (no Coach guarantees, weaker metrics). C only inside admin tooling or heavily sandboxed experiments.

## Blueprint quality metrics

- activation rate (draft → first action)
- D7 / D30 execution rate
- stall rate
- repair recovery rate
- outcome attainment rate
- coach invocation rate (high may mean bad rules)
- safety incidents

A blueprint with high coach usage is often a **bad blueprint**, not a monetization win.

## Versioning & migrations

- Projects pin `blueprint_version` at activation.
- Bugfix patches may be cherry-picked via migration scripts.
- Behavior-changing updates create new version; offer user opt-in “upgrade plan.”

Never silently rewrite an active marathon plan under someone in week 18.

## Critique of Cooking.Carbonara as equal citizen

Recipe blueprints are short-horizon and content-heavy. Training blueprints are long-horizon and rule-heavy.

They share the **engine**, but not the same:

- evidence model
- stall definition
- monetization value
- liability profile

Do not force one UX metaphor to serve both poorly. Share primitives; specialize presentations.
