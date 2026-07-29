# Scaling Strategy

Scaling Facio is three different problems: **content**, **runtime**, **organization**. Confusing them causes bad hires and bad infra.

## 1) Content scale

Bottleneck #1 for years.

### Strategy

- deep, not wide
- Git-based blueprint factory
- domain editors + review board
- simulation tests as CI
- demand signals from failed retrieval → backlog

### Anti-scale

- paying freelancers to spam 5,000 low-quality plans
- LLM-generating taxonomy overnight

### KPI

- % of user intentions covered at high confidence *with* quality bar
- outcome attainment by blueprint

## 2) Runtime / infra scale

Execution engine is OLTP + jobs + push:

- Postgres (or equivalent) for projects/actions/events
- Redis for queues / rate limits
- object storage for media evidence
- vector index as projection
- mobile clients with offline packs

Scale horizontally by user shards only when needed; premature sharding is vanity.

LLM scale:

- route budgets
- provider failover
- circuit breakers
- semantic/playbook caches

## 3) Organizational scale

Early team shape:

- product eng (mobile + backend)
- one AI/platform eng
- one domain designer (fitness or cooking — match wedge)
- part-time trust & safety

Do not hire a 12-person “content ops” before retention.

## Geographic / language scale

- ship one language well
- add second language with string tables + example utterances rebuild
- cultural rule differences need blueprint forks, not just translation

## Domain expansion playbook

For each new domain:

1. outcome ontology slice
2. 10+ blueprints at quality bar
3. safety policy
4. evidence model
5. repair set
6. closed beta metrics vs bar
7. open

No domain launches as “LLM will cover the gaps.”

## Scale risks unique to Facio

- support burden from health/finance advice expectations
- push notification fatigue → uninstall
- multi-project complexity exploding UX

## Critique of “100k intents scale vision”

Scaling utterances/examples is easy.  
Scaling **trusted strategies** is hard.

Invest in:

- editors
- evaluation
- instrumentation

not in vector DB heroics.
