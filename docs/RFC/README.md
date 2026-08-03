# Facio — Internal Product & Architecture RFC

> Working title: **Facio** (repo: `fasio`)  
> Status: Draft RFC v0.1  
> Audience: founders, product, engineering, AI/ML  
> Goal: single source of truth for product philosophy and system design before implementation

---

## What this is

This folder is the foundational design pack for Facio: a mobile system that turns **intent** (“I want…”) into **executed outcomes** (“I did…”) with minimal ongoing LLM cost.

It is intentionally critical. Several popular assumptions in the initial pitch are challenged, replaced, or constrained.

---

## Read order

1. 00 — Vision — North star, non-goals, wedge
2. 01 — Product Philosophy — Outcome product vs chat product
3. 02 — User Journey — End-to-end flows and state machine
4. 03 — Core Principles — Decision rules for product & eng
5. 04 — Domain Model — Entities, invariants, lifecycle
6. 05 — Intent Architecture — Taxonomy, detection, critique of flat intents
7. 06 — Blueprint System — Templates, adaptation rules, cold start
8. 07 — AI Usage Strategy — When LLMs are allowed / forbidden
9. 08 — Cost Optimization Strategy — Unit economics, caching, budgets
10. 09 — Retrieval Pipeline — Hybrid retrieval, ranking, fallbacks
11. 10 — Vector Database Design — Indexes, metadata, freshness
12. 11 — Blueprint Storage — Schema, versioning, publishing
13. 12 — Execution Engine — Deterministic runtime after plan creation
14. 13 — Personalization Pipeline — Slot-filling + constrained generation
15. 14 — AI Coach — Expensive recovery / replan layer
16. 15 — Monetization — What is free, what is paid, what must never be
17. 16 — Scaling Strategy — Content, infra, org scale
18. 17 — Competitive Advantage — Moat realism check
19. 18 — Data Flywheel — Learning loops that actually compound
20. 19 — Network Effects — True vs fake network effects
21. 20 — Risks — Product, technical, legal, market
22. 21 — Anti-patterns — Attractive traps
23. 22 — Things we should NEVER do — Hard constraints
24. 23 — Future roadmap — Phased delivery
25. 24 — Open questions — Decisions still required
26. 25 — Revised architecture — Production stack replacing the 6-layer sketch
27. 26 — Intent Economy — Intent Graph, marketplace, partners, learning, ethics

---

## One-sentence product definition

**Facio is an outcome operating system:** it converts a natural-language intention into a personalized, executable micro-project and runs that project with mostly deterministic logic, escalating to AI only when execution breaks.

---

## Critical stance (read this first)

The initial six-layer stack (Intent → Vector → Blueprint → Personalization → Execution → Coach) is a useful starting sketch, but it is **incomplete and partly wrong**:

1. **100k+ intents is not a goal.** A deep taxonomy of ~200–2,000 high-quality blueprints beats a flat zoo of near-duplicate intents.
2. **Vector search alone is not intent understanding.** Hybrid classification + structured slots + retrieval is required.
3. **“AI almost never used after plan creation” is directionally correct but overstated.** Adaptation events are frequent; the win is making most of them **rule-based**, not “no AI forever.”
4. **Blueprints without an outcome ontology become glorified todo templates.** Differentiation lives in outcome states, evidence of progress, and repair loops — not prettier plans.
5. **Data flywheels are not automatic.** Without instrumentation of success/failure *causes*, you accumulate logs, not intelligence.

These critiques are expanded throughout the docs.

---

## Naming note

Product name in docs: **Facio**. Repository folder may remain `fasio`. Decide brand spelling before public launch; do not rename code paths mid-flight without a migration plan.

---

## Related

**Current product truth (UX / IA / terminology):** [`../Facio 0.1/`](../Facio%200.1/README.md)

Historical product experiments:

- Near-term first slice: [`../mvp/`](../mvp/README.md) (hypotheses, scope, metrics, go/no-go) — frozen
- Next slice (cycles, plugins, executable plan): [`../next/`](../next/README.md) — engine reference; UX superseded by Facio 0.1

RFC remains the long-horizon architecture pack. On navigation, screens, and product nouns, **Facio 0.1 wins** if there is a conflict.
