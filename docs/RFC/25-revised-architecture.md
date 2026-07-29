# Revised System Architecture

This document replaces the original six-layer sketch with a production-oriented stack.

## Original sketch (kept as intuition)

```text
Intent → Vector → Blueprint → Personalization → Execution → AI Coach
```

Useful as a story. Insufficient as a system.

## Revised stack

```text
┌─────────────────────────────────────────────────────────────┐
│ Presentation: Next Action · Contract · Repair diffs · Coach │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Execution Engine (deterministic runtime)                    │
│ Scheduler · State machine · Stall · Playbooks · Evaluators  │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Plan Compiler + Patch Validator                             │
│ Blueprint + slots → PlanGraph · LLM patches must validate   │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Intention Understanding                                     │
│ Policy → Hybrid retrieve/classify → Disambiguate → Slots    │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ Knowledge plane                                             │
│ Outcome taxonomy · Blueprints · Playbooks · Content refs    │
│ Vector projections · Analytics / flywheel jobs              │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│ AI workers (budgeted, tool-constrained)                     │
│ Ambiguity · Slot assist · Patch · Coach                     │
└─────────────────────────────────────────────────────────────┘
```

## Mapping old layers → new

| Old layer | Verdict | New home |
|-----------|---------|----------|
| Intent Detection | necessary but incomplete | Intention Understanding + Policy |
| Vector Search | candidate generator only | Hybrid retrieval inside Understanding / Knowledge plane |
| Blueprint Library | core asset | Knowledge plane + Compiler |
| Personalization | must be compiler-first | Plan Compiler + optional constrained LLM |
| Execution Engine | true product core | Execution Engine |
| AI Coach | paid edge | AI workers + entitlements |

## Critical additions missing from the pitch

1. **Policy gate** before similarity
2. **Outcome taxonomy governance** (not flat intents)
3. **Plan compiler** (not LLM-as-planner)
4. **Patch vocabulary** (diffable mutations)
5. **Playbooks** as first-class cheap coach
6. **Eval harnesses** as release gates
7. **Unit economics observability**

## Reference request flow — create project

```text
User utterance
  → PolicyGate
  → Embed + HybridRetrieve(OutcomeType)
  → Disambiguate?
  → Load Blueprint intake
  → Collect slots (UI)
  → Compile PlanGraph
  → Optional LLM residual patches (validate)
  → Preview Contract + first actions
  → Commit → schedule Actions
  → Execution loop (no LLM)
```

## Reference request flow — stall

```text
Detectors fire
  → Match RepairPlaybook
  → Apply deterministic patches + templated copy
  → If insufficient / user asks → CoachSession (metered)
  → Tools propose patches → user accept → Execution Engine applies
```

## What “minimizing LLM” means operationally

| Path | LLM? |
|------|------|
| Open app, see next action | No |
| Mark done | No |
| Miss 2 workouts → deload suggestion | Usually no |
| “I tore something / rewrite my life plan” | Yes, constrained |
| Brand-new unsupported goal | Prefer no; demand capture |

## Build order for engineering

1. Domain schemas + Blueprint JSON Schema
2. Compiler + scheduler + action API
3. Mobile next-action UX
4. Retrieval + taxonomy seed
5. Playbooks
6. Constrained personalization patches
7. Coach tools + billing meters
8. Flywheel analytics

Anything that inverts this order (Coach demo first) is a red flag.
