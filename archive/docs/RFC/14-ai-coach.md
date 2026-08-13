# AI Coach

## Role

The Coach is the **expensive recovery and strategy layer**, not the daily interface.

Primary jobs:

- interpret messy human situations
- choose / parameterize playbooks
- propose plan patches when rules are insufficient
- explain trade-offs
- hold user to the Contract without shame spirals

Non-jobs:

- small talk companion
- therapist of record
- unlimited life advice oracle

## Triggers

### User-initiated

- “I got sick”
- “No motivation”
- “Rewrite my plan”
- “I don’t have time”
- “This feels too hard / too easy”
- “I hurt myself” → safety protocol first

### System-initiated (careful)

- stall_score crosses threshold **and** playbooks failed / user ignored soft repairs
- ask permission: “Want help adjusting this week?”

Unsolicited chatty coach will feel spammy and burn money.

## Session protocol

```text
1. Load project snapshot (structured)
2. Classify situation → reason codes
3. Try playbook match
4. If playbook sufficient → present parameterized plan diff (may still use tiny model for wording)
5. If not → tool-using LLM proposes patches
6. User accepts / edits / rejects
7. Apply patches via Execution Engine
8. Log outcome for eval + billing
```

## Safety protocol (hard)

For injury, eating disorder signals, self-harm, violence, etc.:

- do not improvise training through pain
- show vetted resources / urge professional help
- restrict certain patch types
- possibly freeze progression nodes

Coach must be policy-aware; “helpfulness” is not the highest value.

## Product surface

Recommended:

- bottom-sheet or session thread **scoped to one project**
- always show proposed diff cards (schedule, volume, swaps)
- “Apply” is the success event, not “AI replied”

Avoid a global Chat tab as home.

## Entitlements

See [Monetization](./15-monetization.md).

Suggested:

- free: playbooks + limited coach sessions / month
- plus: higher caps + priority + deeper strategy modes
- never lock the next deterministic action behind paywall for an active project

## Quality bar

Coach is successful when:

- patch acceptance rate is high
- post-coach 7-day execution rate recovers
- sessions/user/week trends **down** as playbooks improve (good!)
- refund/chargeback and “AI ruined my plan” tickets stay rare

If sessions/user rise forever, you built ChatGPT with guilt.

## Implementation notes

- tool calling mandatory
- JSON patch schema mandatory
- memory = structured project state + last N reason codes, not endless transcript
- store transcripts for trust & safety review with retention limits
- eval set of sticky situations per domain

## Critique: Coach as main subscription hook

Valid **if** free execution is excellent.

Invalid if Coach is compensating for broken blueprints. Users will churn when magic advice still doesn’t get them to act.

Monetize **recovery and advanced strategy**, not oxygen (the next step).
