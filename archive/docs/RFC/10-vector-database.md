# Vector Database Design

## Purpose

Store embeddings that support retrieval for:

1. OutcomeType example utterances
2. Blueprint summaries / applicability text
3. Repair playbook triggers
4. (Later) anonymized successful strategy snippets
5. (Later) content nodes (exercises, recipe steps) for authoring tools

Not every table belongs in a vector DB. Transactional project state stays in primary OLTP.

## Recommended deployment shape

### Early (MVP)

- Start simple: **pgvector** in Postgres (or equivalent) alongside primary data
- Reasons: one ops surface, transactional joins with metadata filters, enough scale for <1M vectors

### Growth

Split when ANN latency/ops demands it:

- dedicated vector service (Qdrant / Weaviate / Pinecone / Vespa — pick based on filter strength + ops skill)
- keep **metadata source of truth** in OLTP; vectors are a projection

**Do not** choose a vector vendor before measuring: MVP taxonomy fits in a small index.

## Collections / indexes

| Collection | Vector of | Metadata filters |
|------------|-----------|------------------|
| `utterance_examples` | example phrase | `outcome_type_id`, `lang`, `policy_class` |
| `outcome_types` | canonical description | `domain`, `ready`, `policy_class` |
| `blueprints` | summary + intake synopsis | `outcome_type_id`, `version`, `status=published` |
| `playbooks` | trigger phrases | `domain`, `repair_class` |
| `content_nodes` (later) | name/description | `type`, `equipment_tags` |

## Embedding strategy

- One primary multilingual embedding model for user-facing retrieval
- Version embeddings: `embed_model_id` stored with each vector
- Re-embed on model change via batch jobs; dual-read during migration

### What to embed

Better: many short example utterances per OutcomeType  
Worse: one long marketing paragraph

Include hard negatives in training/eval, not necessarily in the index.

## Metadata is half the design

Always filter before/within ANN:

```text
lang IN user_langs
policy_class != restricted OR user_eligible
blueprint.status = published
applicability flags compatible when known
```

Unfiltered KNN is how you retrieve postpartum plans for random weight-loss queries.

## Freshness & lifecycle

- published blueprints → upsert vectors
- unpublished → delete/tombstone from index
- taxonomy merge → redirect ids + reassign examples
- keep audit log of index mutations

## Scale estimates (sanity)

Assume mature:

- 3,000 OutcomeTypes × 40 examples = 120k utterance vectors
- 8,000 blueprints summaries
- 5,000 playbook triggers

Trivial for modern ANN. Your hard problem is **quality and governance**, not vector scale.

If someone argues for exotic vector infra because “we’ll have 100M intents,” challenge the product assumption first.

## Privacy

Do **not** casually index raw user intentions containing PII into a shared ANN used for other users.

Aggregation path:

1. cluster anonymous utterances offline
2. human/model-assisted propose new examples
3. publish curated examples only

## Latency budget

Mobile onboarding retrieval: p95 < 200–300ms server-side for candidate gen.

If LLM arbitration is needed, show UI progress and keep deterministic suggestions on screen.
