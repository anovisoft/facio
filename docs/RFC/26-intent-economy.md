# Intent Economy

> Status: Draft RFC v0.1 (strategy horizon: 2–5 years)  
> Depends on: Domain Model, Blueprint System, Data Flywheel, Monetization, Never-do  
> Trigger: strategic review arguing Facio is becoming a platform for human intent, not merely an AI planner

---

## Thesis

If Facio only ships plans and reminders, it is a better habit app with AI seasoning.

If Facio becomes the **trusted runtime where intentions are bound to proven strategies, resources, and repairs** — and later to partners — it can become an **Intent Operating System**: a coordination layer between human desire and the world of tools, services, and products that help fulfill it.

This RFC defines that economy carefully. Ambition is high. Sequencing is ruthless. Commerce that does not raise attainment is rejected.

---

## Non-goals for the near term

- Affiliate marketplace in MVP
- Open blueprint upload for anyone
- Brand-sponsored “Nike marathon plan” as launch marketing
- Replacing the Execution Engine focus with partnership BD

Near-term work remains: wedge outcomes, compiler, playbooks, repair, learning instrumentation.

Intent Economy is the **north map**, not the sprint board.

---

## The economic loop

```text
Intent
  → OutcomeType binding
  → Blueprint (strategy)
  → Project execution
  → Resources / tools / services / products (optional)
  → Evidence of progress
  → Repair when broken
  → Result (attainment / abandon / pivot)
  → Learning back into blueprints & ranking
```

Money may flow in several places later. Trust may only flow if every commercial node is subordinate to attainment.

---

## 1. Intent Graph

### What it is

A structured graph of how intentions relate to the world Facio can operate on — richer than a flat taxonomy and richer than VectorDB similarity.

### Node types (v1 conceptual)

| Node | Meaning |
|------|---------|
| `OutcomeType` | Canonical desired result |
| `Capability` | Skill/asset the user needs or builds (grip strength, knife skills) |
| `Constraint` | Hard limits (injury, budget, no gym, vegan) |
| `Resource` | Things required or helpful (pull-up bar, flour, running shoes) |
| `Blueprint` | Executable strategy package |
| `Playbook` | Repair/adaptation package |
| `Stage` / `ActionTemplate` | Graph internals of blueprints |
| `PartnerOffer` (later) | External product/service attachable to a stage |
| `EvidenceType` | How progress is proven |

### Edge types (examples)

- `OutcomeType` —requires→ `Capability`
- `OutcomeType` —satisfied_by→ `Blueprint`
- `Blueprint` —needs_resource→ `Resource`
- `Blueprint` —blocked_by→ `Constraint` (or `adapts_under`)
- `Stage` —may_use→ `PartnerOffer`
- `Playbook` —repairs→ `FailureMode`
- `Capability` —unlocks→ `OutcomeType` (progressions: first pull-up → 5 pull-ups)

### Why this beats “100k intents”

Intents are utterances. The graph stores **reusable world structure**. Utterances map onto the graph; they do not become 100k product SKUs.

### Relation to VectorDB

```text
Knowledge plane (graph + docs)  = source of truth
Vector index                     = retrieval accelerator over text projections
OLTP project state               = per-user runtime
```

Do not confuse ANN search with ontology.

### Build path

1. Encode OutcomeType ↔ Blueprint ↔ Constraint ↔ Resource in relational/JSON first.
2. Add explicit edges when queries need them (progressions, resource substitutes).
3. Introduce a graph store only if join/query pain is real.

---

## 2. Partner Graph

### Idea

Stages of a journey sometimes need the outside world:

- buy resistance bands
- book a pool lane
- order ingredients
- get a gait analysis
- subscribe to a coaching call

Partners plug into **stages**, not into the home chat.

```text
Run first marathon
  → Blueprint stage: "get reliable shoes"
      → PartnerOffer: vetted shoe fitters / brands
  → Stage: "long run fueling"
      → PartnerOffer: nutrition guides / products (strict rules)
```

### Trust rules (hard)

1. Partner offers appear only when they raise expected attainment or reduce friction for *this* contract.
2. User sees why the offer exists (“needed for stage X”), not a feed of deals.
3. Ranking optimizes for completion lift, not CPC.
4. Disclosure of commercial relationship is mandatory.
5. Sensitive domains (health crisis, ED risk, debt despair) → commercial silence or extreme restriction.
6. Decline partners who require dark patterns, spam, or data resale.

### Anti-pattern

Turning Facio into “intention → shopping mall.” That destroys the Outcome OS brand overnight.

### Sequencing

| Phase | Partner capability |
|-------|--------------------|
| MVP | none (manual resource checklists only) |
| Post-retention | resource links, non-attrib content |
| Later | gated PartnerOffer objects with experiments on attainment |
| Much later | revenue share if ethics + lift proven |

---

## 3. Intent Marketplace (Blueprint Marketplace)

### Idea

Blueprints become first-class objects with provenance:

```text
Run first marathon
  ├── Facio Official
  ├── Community (gated)
  ├── Independent Coach
  ├── Brand (Nike) — highest scrutiny
  └── Club / Gym pack
```

### Why it can matter

- distribution for creators/coaches
- coverage growth without only in-house editors
- eventual B2B2C channel

### Why it can kill you

- unsafe programming
- spam SEO blueprints
- brand capture of UX
- support nightmare
- users cannot tell what is proven

### Marketplace policy (if/when)

1. **Schema compliance** — every listing compiles as a Blueprint DSL.
2. **Safety review** by domain class.
3. **Telemetry mandatory** — attainment, stall, abandon published in aggregate after n-threshold.
4. **Version pinning** — projects don’t silently jump.
5. **Takedown / liability** clear in ToS.
6. **Official vs Third-party** visually distinct.
7. **No pay-to-rank** that overrides quality/attainment scores.
8. Cold-start: invite-only coaches, not open upload.

### Product framing

Marketplace is an **extension of the compiler ecosystem**, not an App Store of PDFs.

---

## 4. Blueprint Evolution (Learning System)

This is the most credible long-term moat in the Intent Economy — and it does not require partners.

### Loop

```text
Blueprint vN in production
  → aggregate funnels (activation, D7 exec, stall, repair, attainment)
  → hypothesize change (intake Q, dose, stage order, playbook)
  → A/B or staged rollout as vN+1
  → keep / revert
  → document causal diff
```

### Example (illustrative)

| Version | Attainment | Note |
|---------|------------|------|
| v18 | 63% | 7 intake questions; week 3 volume spike |
| v19 | 69% | 4 intake questions; earlier deload playbook; removed low-value learning nodes |

The asset is not the percentage. The asset is the **changelog of what caused lift**, under which segments.

### Requirements

- stable identity of nodes across versions (diffable)
- segment-aware metrics (beginner / busy / equipment)
- experiment framework
- human editor in the loop for safety domains
- privacy-safe aggregation

### Critique of naive “auto-evolve with AI”

Auto-mutating blueprints from observational data will overfit survivors and harm edge users. Prefer assisted evolution: models propose, editors + experiments decide.

---

## 5. Recommendation Ethics

Commercial and non-commercial recommendations share one law:

> A recommendation may exist only if it is expected to increase the probability of Contract attainment (or reduce serious harm), not merely to maximize revenue or engagement.

### Practical tests before showing an offer

1. **Necessity** — is this required or strongly instrumental for the stage?
2. **Lift evidence** — any data, or at least expert rationale logged?
3. **Alternatives** — is a free/DIY path shown when viable?
4. **Pressure** — can the user dismiss forever for this project?
5. **Context** — are they in a stall/shame state where selling is predatory?
6. **Disclosure** — is payment relationship clear?

Fail any critical test → do not show.

### Governance

- ethics review for partner categories
- kill-switch for offer classes
- audit samples of shown recommendations monthly once live

---

## 6. Intent OS framing

### Meaning

Facio as OS:

```text
Input (intent)
  → Bind
  → Project
  → Execute
  → Recover
  → Complete
```

External apps become **plugins**:

- HealthKit as evidence plugin
- Calendar as scheduler plugin
- Shop API as resource plugin
- Human coach app as accountability plugin
- Creator studio as blueprint authoring plugin

### What must exist first

An OS without a working kernel is a press release.

Kernel = Execution Engine + Blueprint compiler + Repair + Contract.

Plugins after the kernel is loved.

### API surface (future sketch)

- create/bind project from OutcomeType
- push evidence events
- propose/apply plan patches (permissioned)
- read next action (for widgets / wearables)
- publish blueprint artifact (partner tier)

---

## 7. Knowledge plane (graph-first mental model)

Replace “we have a VectorDB” with:

```text
Knowledge plane
  ├── Ontology / Intent Graph
  ├── Blueprint registry
  ├── Playbook registry
  ├── Content nodes
  ├── Partner offers (later)
  └── Projections
        ├── Vector indexes (utterances, summaries)
        ├── Search documents
        └── Analytics marts
```

VectorDB is an index. The graph/ontology is the meaning layer. Both are needed; neither alone is Facio.

---

## Monetization inside the Intent Economy

Possible future revenue (ordered by trust risk):

1. Subscription for Coach / multi-project / advanced repair (already primary)
2. Creator revenue share on premium blueprints (after quality system)
3. Partner take-rate on instrumental offers (highest brand risk)
4. B2B seats for coaches/gyms using Facio as delivery OS

**Never** make partner take-rate the primary growth metric.

---

## Competitive reading

| Worldview | Product becomes |
|-----------|-----------------|
| ChatGPT wrapper | disposable |
| Habit tracker + AI | crowded commodity |
| Outcome runtime | sticky utility |
| Intent Economy / OS | category-defining — only if ethics + attainment hold |

The review is right that platform-for-intent is the interesting endgame. It is wrong if that fantasy rearranges the roadmap ahead of completion loops.

---

## Risks specific to Intent Economy

1. **Affiliate capture** — ranking follows money
2. **Marketplace spam** — quality collapse
3. **Brand bullying** — exclusive deals warp recommendations
4. **Privacy** — graph learning leaks sensitive intentions
5. **Over-graphing** — years spent modeling the world, zero users finish pull-ups
6. **Regulatory** — health/finance offers cross advice boundaries

---

## Phased adoption

### Phase A — Graph-ready data model (now-ish)

- explicit OutcomeType, Resource, Constraint, Capability fields
- no marketplace UI

### Phase B — Evolution console

- blueprint version metrics + diffs
- experiment hooks

### Phase C — Controlled partners

- resource deep links with ethics checklist
- attainment experiments

### Phase D — Invite-only blueprint publishing

- coaches/creators under schema + safety + telemetry

### Phase E — Intent OS APIs

- widgets, coach portals, selective plugins

---

## Open questions

1. Do we ever allow brand-named blueprints, or only neutral official + independent coaches?
2. What attainment lift threshold justifies a PartnerOffer staying listed?
3. Who owns ethics review — product, trust & safety, or external board?
4. Is Capability a first-class node in v1 schemas or derived from blueprint stages?
5. Geographic partner graphs — how localized before it becomes ops hell?

---

## Decision

Adopt **Intent Economy as a strategic horizon document**.

Do **not** prioritize marketplace or partner revenue until:

- wedge attainment bars are hit
- blueprint evolution loop is staffed
- recommendation ethics are written into product code paths, not only markdown

The unusual company is not the one that can generate plans.  
It is the one that becomes the **trusted operating system for getting intentions across the finish line** — with commerce, if any, as a servant of that trust.
