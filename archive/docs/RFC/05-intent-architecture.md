# Intent Architecture

## Problem with the naive model

Initial proposal:

```text
"Хочу похудеть" → fitness.weight_loss
```

Then vector-search similar goals, then pick a blueprint.

This fails in production for several reasons:

1. **Utterance ≠ outcome.** “Похудеть” may mean aesthetics, health markers, clothing size, or sport performance.
2. **Near-duplicates explode.** “lose 5kg”, “lose belly”, “get lean”, “cut” create junk taxonomy if each is an “intent.”
3. **Constraints dominate strategy.** Same outcome + different constraints ⇒ different blueprints (injury, vegan, no gym, postpartum*).
4. **Multilingual / slang / code-switching** breaks brittle classifiers.
5. **Policy risk** hides inside innocuous phrasing (“extreme cut”, “teen weight loss”).

\* Postpartum and medical-adjacent paths need clinical-safe positioning; do not improvise medical advice.

## Recommended model: layered intent understanding

```text
Raw utterance
  → Policy gate (block / escalate / allow)
  → Language normalize + embed
  → OutcomeType candidates (classifier + retrieval)
  → Disambiguation (if needed)
  → Slot hypotheses
  → Blueprint shortlist (OutcomeType × constraint features)
  → Bind
```

Intent is not a single label. It is a **bundle**:

```ts
type ResolvedIntention = {
  outcomeTypeId: string;
  confidence: number;
  slots: Record<string, unknown>;
  constraintFeatures: string[];
  policyClass: "standard" | "sensitive" | "restricted";
  blueprintCandidates: { id: string; score: number }[];
};
```

## Taxonomy design

### Prefer hierarchy over flat 100k intents

```text
fitness
  strength
    pullup_first
    pushup_first
  endurance
    run_5k
    run_marathon
  bodycomp
    fat_loss_general
cooking
  recipe
    carbonara
finance
  save
    emergency_fund
behavior
  cessation
    smoking
```

### Target scale (honest)

| Horizon | OutcomeTypes (curated) | Blueprints (incl. variants) |
|---------|------------------------|-----------------------------|
| MVP | 15–40 | 30–80 |
| Year 1 | 150–400 | 300–800 |
| Mature | 1,000–3,000 | 3,000–10,000 |

“100,000 intents” should mean **100,000 utterance examples / embeddings mapped into the taxonomy**, not 100,000 productized outcome types.

If you ship 100k outcome types, you will not quality-control them. That is content bankruptcy.

## Detection stack

### Layer A — Policy classifier (cheap, mandatory)

Rules + small model:

- self-harm
- eating disorder patterns
- medical emergency
- illegal activity
- minors in adult contexts

Outputs: `allow` | `soft_block_with_resources` | `hard_block` | `human_review`.

### Layer B — Outcome retrieval + classification (hybrid)

Do **not** choose only one of:

- zero-shot LLM classification (expensive, unstable)
- pure vector KNN (confused by paraphrases and constraints)

Use hybrid:

1. embed utterance
2. retrieve top-K OutcomeType docs + example utterances
3. optional small classifier / cross-encoder re-rank
4. LLM only if top scores are close / below threshold (budgeted)

### Layer C — Slot extraction

Prefer:

- schema-driven extraction against blueprint question set
- chip UI confirmation rather than trusting silent extraction

LLM slot fill is allowed when recall of structured extractors fails — still confirm with user for high-impact slots (injuries, budget, deadlines).

## Ambiguity handling UX

When top-2 OutcomeTypes are within margin ε:

Show cards:

- “Lose fat / improve body composition”
- “Train for a sport / performance”
- “Build a general healthy routine”

Never pretend certainty.

## Mapping examples

| Utterance | Bad label | Better resolution |
|-----------|-----------|-------------------|
| Хочу похудеть | `fitness.weight_loss` only | disambiguate + slots: target, timeline, training access |
| Убрать живот | same as fat loss? | often `bodycomp.fat_loss` with focus tag, not new OutcomeType |
| Хочу карбонару | recipe intent | `cooking.recipe.carbonara` + diet constraints |
| Накопить деньги | too broad | force slot: amount + purpose → emergency fund vs vacation vs debt |
| Сменить работу | career mega-domain | **defer** until engine mature; or narrow wedge “interview prep for role X” |

## Intent library assets (what to store)

For each OutcomeType:

- canonical description
- positive/negative example utterances (multilingual over time)
- embedding centroids / example vectors
- required slots
- forbidden adjacent types (confusion set)
- policy class
- default blueprints by constraint features

## Critique of Vector-Search-as-Architecture

Vector search is a **retrieval tool**, not an understanding architecture.

If Layer 2 in the original pitch is “find similar goals,” the system will match surface semantics and miss:

- feasibility
- policy
- duration class
- evidence class

Keep vectors. Demote them from “architecture spine” to “candidate generator.”

## Open taxonomy governance

Who can add OutcomeTypes?

- Early: founders + domain editors only
- Later: proposal pipeline with quality gates (examples, blueprint, success criteria, safety review)

User-generated “intents” can suggest clusters; they must not auto-publish as taxonomy nodes.
