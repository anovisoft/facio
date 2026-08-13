# Data Flywheel

## Desired loop

```text
More users execute projects
  → more structured events (done/skip/stall/repair/outcome)
  → better blueprint rules & rankings
  → higher attainment & retention
  → more users
```

This only works if data is **structured, consented, and decision-relevant**.

## What to collect (high value)

- intention text → bound OutcomeType (and rebinds)
- slot distributions
- action completion / skip reasons
- stall causes (taxonomy)
- repair type → recovery success
- time-to-first-action
- outcome attainment / abandon reasons
- coach patch accept/reject
- notification response rates

## What not to fetishize

- raw chat transcripts as the learning corpus
- cosine similarities without outcomes
- vanity “knowledge base size”

## Flywheel layers

### Layer 1 — Editorial analytics (ship first)

Dashboards for blueprint owners:

- funnel by blueprint
- where users drop
- which nodes are skip magnets

Humans change YAML rules. This already compounds.

### Layer 2 — Rankers & defaults

- better default doses by segment
- better OutcomeType priors by locale
- better disambiguation options ordering

### Layer 3 — Adaptive policy learning

- bandits / uplift models for repair choice
- propensity to stall models → proactive shrink

Requires sample size and experimental hygiene.

### Layer 4 — Assisted blueprint mining

Cluster unsuccessful custom goals → propose new OutcomeTypes → human publish.

## Causal humility

Observational data will say wrong things:

- survivors who finish hard plans look like hard plans work (selection bias)
- users who open Coach might already be struggling more

Prefer:

- A/B on repairs and defaults
- pre-registered metrics
- segment-aware evaluation

## Privacy & trust

- clear consent
- retention limits
- no sale of personal intention data
- aggregate before cross-user learning
- careful with media evidence

Flywheel dies if users feel surveilled.

## Cold start

Flywheel does not invent initial quality. Expert blueprints do.

Claiming “we’ll get smart from users” as a substitute for domain design is a common startup delusion.

## Critique of the pitch’s flywheel

The pitch assumes automatic improvement from “each new user.”

Reality: each new user adds noise unless you instrument **failure causes** and close the loop to blueprint versions.

Build the closed loop explicitly or you will only grow a data lake.
