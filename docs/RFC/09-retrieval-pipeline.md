# Retrieval Pipeline

## Role of retrieval

Retrieval finds **candidate structures** (OutcomeTypes, example utterances, blueprints, playbooks, content nodes). It does not “understand” the user alone.

## End-to-end pipeline

```text
1. Normalize text (lang detect, spell lightly, strip filler)
2. Policy screen
3. Embed utterance
4. Candidate generation (ANN + lexical + rule hints)
5. Feature enrichment (constraints keywords, duration heuristics)
6. Re-rank (cross-encoder or gradient booster on features)
7. Thresholding / disambiguation decision
8. Blueprint shortlist by OutcomeType × slots
9. Compile or escalate
```

## Candidate generation (hybrid)

### Dense (vectors)

- utterance → OutcomeType examples
- utterance → Blueprint descriptions
- failure message → RepairPlaybooks

### Sparse / lexical

- keyword overrides (“марафон”, “carbonara”, “бросить курить”)
- domain dictionaries
- brand/recipe proper nouns

### Rule hints

- regex/entity for numbers (“5 кг”, “10 недель”, “$2000”)
- equipment mentions
- time budgets

Relying only on dense retrieval will miss exact entities and overfit paraphrases.

## Re-ranking features (examples)

- dense score
- lexical overlap
- prior popularity of OutcomeType in locale
- user history affinity (past domains)
- policy compatibility
- blueprint coverage readiness (don’t rank uncovered types high)
- expected horizon match (user implies “tomorrow dinner” vs “6 months”)

## Decision thresholds

| Situation | Behavior |
|-----------|----------|
| top1 ≥ T_high and margin ≥ M | auto-bind candidate |
| top scores close | disambiguation UI |
| top1 < T_low | nearest-neighbor suggestions + custom scaffold / reject |
| policy sensitive | special flow, ignore pure similarity |

Calibrate T/M on golden sets per language.

## Fallback ladder

1. exact alias match
2. hybrid retrieval
3. disambiguation
4. “closest supported goals”
5. limited custom project
6. capture demand signal for taxonomy team

Never silently invent a fake OutcomeType id.

## Personalization retrieval (later)

Retrieve “people like you succeeded with strategy S” — only when:

- enough n-size
- privacy aggregation ok
- causal naivety acknowledged (correlation ≠ prescription)

Until then, prefer expert blueprints + rules.

## Evaluation

Offline:

- recall@K OutcomeType
- binding accuracy after UI
- harmful retrieval rate (should be ~0)

Online:

- disambiguation rate
- rebind rate within 24h (user says “wrong goal”)
- time-to-first-action after retrieval

## Critique of original Layer 2 example

Matching “похудеть” to “похудеть после беременности” via vectors can be **dangerous**, not helpful, if it auto-selects a postpartum blueprint without eligibility gates.

Retrieval must be filtered by **applicability predicates**, not just cosine similarity.
