# Personalization Pipeline

## Goal

Turn `Blueprint + slots + user profile` into a valid `PlanGraph` + schedule with minimal generative cost and maximal safety.

## Pipeline stages

```text
1. Bind blueprint (id, version)
2. Validate slots against intake schema
3. Infer missing low-impact slots with defaults
4. Apply mixin / rule composition
5. Compile PlanGraph
6. Validate graph + dose sanity
7. Schedule
8. Residual gap detection
9. Constrained LLM patch (optional)
10. User preview + commit
```

## Slot tiers

| Tier | Examples | Missing behavior |
|------|----------|------------------|
| Critical | injuries, days/week, equipment | block compile; ask user |
| Material | diet style, budget band | ask or disambiguate |
| Soft | preferred vibe, music while cooking | default; never block |

## Compilation (deterministic)

A compiler module maps slots → graph:

- choose node variants (`band_assisted` vs `foot_assisted`)
- set dose parameters from look-up tables
- set stage durations
- attach evidence requirements

Compiler must be unit-tested per blueprint.

## Residual gaps

Gaps that may justify LLM patch:

- unusual constraint combo not covered by rules
- user free-text note that implies schedule nuance
- localization edge where template copy missing (microcopy only)

Gaps that should **not** justify LLM:

- “make it more motivational”
- “add more educational content”
- “invent a novel periodization because fun”

## Constrained generation contract

LLM output = list of patch ops, e.g.:

```json
{
  "patches": [
    { "op": "SWAP_NODE", "from": "run_interval", "to": "walk_interval", "reason_code": "knee_pain" },
    { "op": "REDUCE_VOLUME", "pct": 20, "stages": ["foundation"] }
  ],
  "user_summary": "short"
}
```

Validation:

- ops allowed for blueprint
- parameters in range
- resulting graph still compiles
- policy checks pass

On failure: discard patches; ship deterministic plan; flag analytics `personalization_patch_rejected`.

## Preview UX

Before commit, show:

- weekly time claim
- first 3 actions
- success definition
- key assumptions (“assumes bar access”)

Allow slot edits → recompile (cheap).

## Continuous personalization (after start)

Prefer event-driven rules:

- if RPE high → reduce
- if too easy → progress
- if misses → shrink

Use ML later for **propensity models** (who stalls when), not for rewriting prose daily.

## Critique of “LLM changes only necessary parts” without compiler

If there is no compiler, the LLM is inventing the plan while being told it is “only patching.” That is self-deception.

**Compiler-first personalization** is the scalable architecture. LLM is a safety valve, not the factory.
