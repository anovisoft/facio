# User Journey

## Journey map (canonical)

```text
Spark → Capture → Clarify → Contract → Personalize → Commit
  → Execute → Review → (Stall?) → Repair → Resume
  → Complete | Abandon | Pivot
```

## Phase detail

### 1. Spark

User arrives with a raw intention:

- typed: “хочу научиться подтягиваться”
- voice
- deep link from content (“Start carbonara path”)
- suggestion from prior projects (“People who finished X often start Y”) — later

**Job of this phase:** accept messy language without forcing categories upfront.

### 2. Capture

System produces a structured draft:

- candidate `OutcomeType`
- confidence
- ambiguous alternatives (“lose weight” vs “build muscle” vs “get healthier”)

If confidence is low, show **disambiguation cards**, not an interrogation form.

### 3. Clarify (slot filling)

Ask **minimum necessary** questions from the matched blueprint’s question set.

Rules:

- Max ~5 questions on first create for most blueprints (hard UX budget).
- Prefer multiple choice / sliders / chips over free text.
- Free text only when slots cannot be enumerated.
- Never ask what can be inferred later from behavior.

### 4. Contract

Show the outcome contract before plan generation:

- what “done” means
- expected weekly time
- non-negotiables (equipment, diet style, budget)
- safety notes where relevant

User confirms: **This is the result I’m buying.**

### 5. Personalize

System instantiates Blueprint → Project Plan:

- mostly template + slot substitution
- constrained LLM patch only for residual gaps
- schedule anchored to user’s availability

### 6. Commit

Critical behavioral moment:

- schedule first action (ideally today / tomorrow)
- enable notifications with explicit consent
- optionally set “minimum viable week” (anti-perfectionism)

Without commit, project stays `draft` and should not count as activation.

### 7. Execute (default daily loop)

Home shows **one primary next action**:

- title
- why it matters (one line)
- how long
- done / skip / need help

Secondary: week overview, streak-of-consistency (not gamified casino), progress toward outcome.

**AI is not in this loop by default.**

### 8. Review

Cadence depends on blueprint:

- daily micro-check for habits
- weekly review for training / finance
- milestone reviews for long projects

Reviews are structured forms + computed stats, not chat.

### 9. Stall detection

Stalls are first-class:

Signals:

- missed N consecutive actions
- declining completion rate
- explicit “I’m struggling”
- calendar conflict density
- self-reported mood/motivation (optional)

System response priority:

1. rule-based soften / reschedule
2. canned repair playbooks
3. AI Coach (paid / limited)

### 10. Repair

Repair outcomes:

- reschedule
- reduce load (deload week)
- swap strategy branch
- pause with return date
- pivot outcome (new contract)

### 11. Complete / Abandon / Pivot

**Complete:** success criteria met → celebration that is short, then “what’s next?”

**Abandon:** explicit or inferred; capture reason taxonomy (critical for flywheel).

**Pivot:** keep history, new contract, transfer reusable assets (equipment profile, schedule preferences).

## Example journey: “Learn pull-ups”

1. Capture → `fitness.strength.pullup_first`
2. Clarify → experience, bodyweight band access, days/week, injuries
3. Contract → “1 clean pull-up in ~10 weeks, 3×/week, 20–30 min”
4. Plan → scapular pulls → dead hangs → band assisted → negatives → attempts
5. Day 1 action scheduled tonight
6. Week 3 illness → rule: deload + shift dates; if pain reported → coach/safety path
7. Week 9 first pull-up logged → project complete → suggest “3 pull-ups” progression blueprint

## Example journey: “Cook carbonara”

1. Capture → `cooking.recipe.carbonara`
2. Clarify → kitchen tools, dietary constraints, skill level
3. Contract → “cook authentic carbonara once with acceptable technique”
4. Plan → shopping list → mise en place drill → sauce technique → full cook → critique checklist
5. Execution is short (days, not months) — blueprint duration must match reality
6. Completion evidence: photo + self-score checklist (optional)

## Anti-journey (what we refuse)

- Endless clarifying chat before any plan
- Generating a 40-step plan with no first action
- Daily motivational essays
- Forcing social share to continue
- Requiring premium just to see the next step of an already paid/created plan (trust breaker)

## State machine (product-level)

```text
draft → active ⇄ paused
active → stalled → active (repaired)
active → completed
* → abandoned
* → pivoted (spawns new project, archives old)
```

Engineering detail lives in [Domain Model](./04-domain-model.md) and [Execution Engine](./12-execution-engine.md).
