# AI Usage Strategy

## Principle

**LLMs are intermittent workers, not the runtime.**

If the app cannot serve tomorrow’s next action while the model provider is down, architecture has failed.

## Allowed AI jobs (runtime)

| Job | When | Model class | Must be constrained? |
|-----|------|-------------|----------------------|
| Ambiguous intent arbitration | Low classifier confidence | small/medium | Yes — pick from candidates |
| Slot extraction assist | Structured extract fails | small | Yes — JSON schema |
| Personalization patch | Residual gaps after template bind | medium | Yes — patch ops only |
| Microcopy localization / tone | Missing string variants | small / cache | Yes — short strings |
| Coach repair dialogue | User or system escalate | medium/large | Yes — project-bound tools |
| Plan critique | User asks “does this make sense?” | medium | Yes — read-only then propose patch |

## Forbidden AI jobs (runtime, v1–v2)

- freeform lifelong chat unbound from a project
- generating brand-new multi-week programs from scratch as default path
- unsupervised medical / legal / financial advice beyond policy templates
- autonomous infinite replanning loops
- generating marketing content inside the execution loop
- “companionship” / romantic / parasocial modes

## Model routing

```text
request
  → can rules/retrieval solve? → do that
  → can small model + schema solve? → small
  → needs reasoning over project state? → medium + tools
  → user explicitly paid for coach depth? → larger, still tooled
```

### Tool-using coach > chat essay

Coach should call tools:

- `get_project_snapshot`
- `propose_schedule_shift`
- `propose_volume_change`
- `apply_playbook`
- `create_plan_patch`

Final user-visible text is secondary to **accepted patches**.

## Context packaging (cost + quality)

Never dump full chat history.

Send:

1. Contract summary
2. Current stage + next 7 actions
3. Last 14 days execution stats
4. Trigger reason + user message
5. Allowed patch vocabulary for this blueprint
6. Safety policy snippet for domain

Hard token budgets per job type.

## Caching

Cache aggressively:

- embeddings of taxonomy / examples
- compiled blueprint JSON
- frequent personalization snippets
- coach answers to frequent trigger classes (playbook-first)

Semantic cache for coach: only when risk is low and answers are playbook-equivalent.

## Evaluation harness (non-optional)

Before expanding AI usage:

- golden set of intents → expected OutcomeTypes
- personalization cases → expected patch ops
- coach cases → expected playbook / patch class
- safety cases → must block / must escalate

Ship gates: regression thresholds on these suites.

## “AI as internal mechanism” UX implication

Users may not need to know which model ran.

They **do** need to know:

- what changed in their plan
- why
- how to undo

Transparency of **plan diffs** > transparency of model brands.

## Critique of original Layer 4

> “LLM receives Blueprint + user data and changes only necessary parts.”

Good direction. Make it stricter:

1. Compiler produces a fully valid plan without LLM when slots are complete.
2. LLM may only emit **JSON patch operations** validated against schema.
3. If validation fails, discard and fall back to template defaults — never show raw model plan.

This single decision prevents 80% of “AI broke my workout” disasters.
