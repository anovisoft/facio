# Cost Optimization Strategy

## Unit economics target

Define early (even if numbers are guesses):

```text
Gross margin per active project / month =
  ARPU_allocated − (LLM + push + storage + support + infra)
```

If Coach is the paid wedge, free tier must be nearly LLM-free after onboarding.

### Suggested early budgets (illustrative, calibrate with real pricing)

| Phase | LLM $/MAU/month target | Notes |
|-------|------------------------|-------|
| Onboarding only | $0.02–$0.10 | Most users cached/template |
| Active free execution | ~$0.00–$0.03 | anomalies only |
| Coach subscriber | $0.30–$1.50 | depends on caps |
| Heavy coach abuser | hard capped | queue / degrade |

These are **design constraints**, not forecasts.

## Cost levers (in order of leverage)

1. **Don’t call the model** — rules, playbooks, templates
2. **Call a smaller model** — classification, slots, microcopy
3. **Shorten context** — snapshots, not histories
4. **Constrain outputs** — patches, enums, JSON schemas
5. **Cache** — embeddings, frequent repairs, compiled plans
6. **Batch / async** — non-interactive personalization
7. **Precompute** — offline blueprint improvements
8. **Rate limit** — productized scarcity for Coach

## Architecture tactics

### Onboarding path

Ideal happy path:

```text
embed (local or cheap API)
→ ANN retrieve OutcomeTypes
→ rules pick blueprint
→ UI slots
→ compile plan (no LLM)
→ done
```

LLM only on ambiguity / policy edge / custom escape hatch.

### Execution path

Push notifications + local/server schedule engine. Zero tokens.

### Stall path

Try playbooks first. Count playbook resolution rate as a cost KPI.

### Coach path

Metered:

- N sessions / billing period
- or soft unlimited with abuse detection
- always tool-constrained

## Product decisions that secretly explode cost

| Decision | Cost impact |
|----------|-------------|
| Daily AI “motivation message” | catastrophic at scale |
| Always-on voice companion | catastrophic |
| Regenerating full plan on every miss | high + UX churn |
| Long chat memory in every call | high |
| Multimodal video form checks by default | high + privacy |
| Supporting “any goal” via LLM blueprints | unbounded |

## Observability requirements

Per request:

- route name
- model
- input/output tokens
- cache hit
- project id / blueprint id
- billed vs free tier attribution

Dashboards:

- $ / activated project
- $ / coach session
- token burn by route
- playbook vs LLM resolution ratio

## Cost-quality trade-off policy

Never “optimize” by removing safety classifiers.

Prefer saving money on:

- motivational copy
- redundant summaries
- full replans
- verbose coach essays

## Cheaper system design alternatives worth adopting

1. **On-device small models** later for intent/slot (privacy + cost) once quality allows.
2. **Compiled FAQ coach**: many “I have no motivation” cases are a 3-step UI wizard, not a chat.
3. **Weekly batch insights** instead of live generative summaries.
4. **Human-authored content packs** for recipes/exercises stored in CDN, not generated.

## Critique: “Coach in subscription = problem solved”

Subscription revenue does not automatically cover generative cost if:

- free users still burn tokens in onboarding
- coach prompts are huge
- users learn to use coach as daily chat

Metering and playbook-first design are mandatory even for paid tiers.
