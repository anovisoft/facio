---
name: facio-product
description: Facio product law for implementation. Use when writing or reviewing Facio code, docs/state, lid/desk/widget/cue/drift/talk work, or when a change could violate RFC never-do.
---

# Facio product

Read [`docs/state/README.md`](../../../docs/state/README.md) before coding. Product truth is [`docs/rfc/`](../../../docs/rfc/README.md). Do not rewrite RFC to justify a feature.

## Object

Reason + cadence + drift live in one `Subject`. A `Cue` without `surface` is rejected. The lid is a projection of what is due now, not a second inventory. Chat snapshots are pictures, not runtimes.

## Hard stops

- Lid, ticks, timers, drift, reminder time: no LLM.
- Home is the lid, not a prompt. No bottom tabs. Category tabs stay parked.
- Drift is arithmetic. A drift ask offers shrink / retire, never "try harder".
- Pain is a boundary: technique and a smaller number. Never raise target or cadence through pain.
- A conclusion left as text only is a bug.
- Do-time copy is a short command in the user's language. Do not overwrite it with a lecture.
- Done today stays in Today, dim, until midnight. Not Lifetime.
- Use cannot swipe to another instance. Inspect can.
- No Guide / Episode / Path / Plan Feed nouns. No sourced media library.

## Wedge

Ship the founding loop to production quality: counter + tick + reminder, cue at do-time, window, drift card, talk that materializes. Pan / Deeds / Inspect — step 5, accepted PO at minimum (2026-08-19). Founding lid+pan accepted as a dogfooded hypothesis the same evening. Next: waves **В1–В3** in `docs/state/plan.md` (accepted PO 2026-08-20). **В1.0–В1.2 done.** Next **В1.3**. Talk-created gym has no reminder until miss or an explicit clock. Voice, cooking, sports-corpus RAG — only if PO says so. Lead = PM; human = PO; Task subagents = developers (skills named per `AGENTS.md`).

Impressive = that loop on a native lid, readable in a ~90s recording. Not catalog breadth.

## After a change

If the change alters product behavior, update RFC first, then `docs/state`. If it only moves an engineering step, update `docs/state` only.
