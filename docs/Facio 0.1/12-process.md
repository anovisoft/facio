# 12 — Process (PO / PM / agents)

How we implement Facio 0.1 after context compression.

---

## Roles

| Role | Who | Owns |
|------|-----|------|
| **Product Owner** | Human (you) | Priorities, dogfood accept/reject, open product decisions, taste |
| **Project Manager** | Lead agent in this chat | Slice scope, briefs for subagents, merge order, doc updates, escalate blockers |
| **Developers** | Task subagents | Implement one slice per run; no silent product invention |

Default subagent model: **Cursor Grok 4.5 High** for explore/implement/review. Composer 2.5 only for cheap mechanical lookups (workspace rule).

---

## Cadence

```text
PO sets / confirms priority
  → PM writes slice brief (DoD, files, non-goals, open questions)
  → Dev subagent implements ONE slice
  → PM reviews vs Facio 0.1 + brief
  → PO dogfoods (or PM smoke) → accept / iterate / next slice
```

Rules:

1. **One slice per subagent run** — no “build all of 0.1”.  
2. Spec truth = `docs/Facio 0.1/` — especially [11](./11-success-systems.md).  
3. Engine reference = `docs/next/` + `apps/` — do not throw away cycles/plugins/physical day.  
4. If product ambiguity blocks coding → **stop and ask PO** (list in [10](./10-agent-brief.md) / [13](./13-continuity.md)).  
5. After each accepted slice → update [13](./13-continuity.md) status table.  
6. External users still early — dogfood first (carbonara + push-ups).

---

## What PM does each turn

1. Point to current slice in [14](./14-impl-plan.md)  
2. Paste a self-contained brief to the subagent (paths, DoD, anti-goals, “read Facio 0.1 X”)  
3. On return: check DoD, lints/tests if relevant, doc continuity  
4. Tell PO: what to dogfood, what was deferred, what needs a decision  

What PM does **not** do: invent Focus weights, streak rules, or visual design without PO when listed as open.

---

## What PO does

- Accept / reject slices after dogfood  
- Decide open questions when PM escalates  
- Can reorder slices in [14](./14-impl-plan.md)  
- Can pause shell work for engine work (e.g. time travel) if dogfood blocked  

---

## Why this model (vs alternatives)

| Approach | Verdict |
|----------|---------|
| **PO + PM + slice subagents** (this) | Best fit — already worked for `next/` slices 1–5 |
| One mega-agent builds everything | Context rot, weak DoD, hard dogfood |
| Spec-only then hand to humans | Fine later; now you want agent velocity |
| Parallel many slices at once | Only for non-overlapping files; default serial |

**Recommendation: do this.** Before chat summary: docs below are the memory. After summary: PM starts at Slice A unless PO says otherwise.

---

## First message after summarization (template)

PO can paste:

> Ты PM. Я PO. Спека: `docs/Facio 0.1/`. Continuity: `13`. План: `14`.  
> Запусти Slice A субагентом. Не изобретай product decisions из open list.
