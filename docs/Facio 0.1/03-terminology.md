# 03 — Terminology

Canonical vocabulary for Facio 0.1. Prefer these in UI copy and new code.  
Legacy prototype names → mapping in [08](./08-migration-from-prototype.md).

---

## Intent

What the user wants. Ephemeral until it becomes a Guide.

Example: *“I want to cook carbonara.”*

Capture surface: **Create** — one big field, e.g. *What do you want?*  
Not: Create Project / New Goal / Plan.

## Guide

**Primary product entity.**

The path from current state to the result. Users see **Guides**, not Projects or Plans.

Contains: outcome/result, success criteria, Cycles, Sessions, progress.

Guide is also a **screen** (beautiful roadmap) — see [05](./05-screens.md).

## Commitment

The moment the user agrees to start the Guide.

- Before: Guide is a proposal (Explore).
- After: Guide is **active**; Sessions appear on Continue.

UI gesture example: **Start Guide**.

Commitment requires having seen the path (P4).

## Cycle

Guide is split into Cycles (typically ~7 days; sometimes 1–14).

After a Cycle ends, the system can assemble the next Cycle from results + optional clarify.

User mostly feels Sessions; Cycle is the progress boundary.

## Session

**Minimal daily product unit.**

Answers: *What do I do right now?*

This is what the user opens most days. After finishing — leave the app; return tomorrow.

A Session has one (or a small set of) **UI Blocks** and a clear Done.

## UI Block

Executable interface piece inside a Session.

Closed set owned by the client (not freeform LLM widgets). Examples:

| Block | Typical use |
|-------|-------------|
| Timer / TimerStack | Isolated countdown |
| Timeline | Cooking session axis + markers |
| Stepper | Strength: measure / work / rest beats |
| Interval | HIIT by seconds |
| Counter / Dose | Single count target |
| Checklist | Shopping / prep / binary items |
| Reading | Long-form step content |
| Flashcards | Language drills |
| Video | Watch-along |
| Form | Structured input |
| Progress | In-session progress chrome |

Facio ≠ todo list because Sessions are **block-driven**, not text-driven.

Prototype plugins (timeline, stepper, …) are the seed of UI Blocks.

### Session presentations (same Session, three contexts)

Not S/M/L size confusion — **roles**:

| Name | Where | Job |
|------|-------|-----|
| **Hero Preview** | Continue | See the action with eyes (fragment of Block state). **Read-only** in 0.1 |
| **Full Block** | Session | Complete interactive execute |
| **Compact Summary** | Guide roadmap | Point on the path among many Sessions |

Every Block type **must** be able to render Hero Preview + Full Block; Compact Summary may be title + status mark on the roadmap.

Hero Preview ≠ shrunk Full Block (separate read-only view — avoids dual-execute code). Interactable checkboxes on Continue are a later option; architecture stays the same.

## Repair

When the user drifts from the plan, the Guide is repaired.

May account for: missed days, new constraints, changed goal, lighter load, schedule shift.

Product-visible, fast, not chat-only.

## Continue

Home surface: **Focus-ranked** ready Sessions across active Guides.

Not a news feed. Not a chat. Not a full Guide list.  
Order comes from **Focus Engine** — see [11](./11-success-systems.md).

## Focus / Focus Engine

Product system that ranks Sessions on Continue and picks the single best **Focus** Session (*if only one card — which?*).

## Cover

Emotional identity card of a Guide: emoji/mark, title, difficulty, duration summary (e.g. *Easy · 25 min · 3 sessions*). Used on Continue, drawer, Guide header.

## Identity

Per-Guide story layer while active: started date, progress to outcome, streak, completed / repaired / skipped counts.  
Answers: *this is my path* — not a social profile. Lives on Guide.

## Session complete

End-of-Session victory beat (progress resolve + “Session complete”), before returning to Continue.

## Finish Experience

End-of-Guide celebration + stats + CTAs (Repeat / Start next Guide). Turns Guide into a finished story.

## Diff (Repair / AI Edit)

Human-readable before → after preview required before applying structural mutations.

## Undo

Restore previous Guide state version after Repair / AI Edit / structure edit.

## Explore Mode / Execute Mode

Behavioral modes, not separate apps:

- **Explore** — studying/editing Guide, pre-Commitment and on demand
- **Execute** — living in Session after Commitment

---

## Words to avoid in primary UI

| Avoid as primary | Prefer |
|------------------|--------|
| Project | Guide |
| Plan / Path (as product noun) | Guide |
| Task / Action / Todo | Session step / UI Block content |
| Chat / Ask AI (as home) | — |
| Accept path (duplicate map) | Start Guide (Commitment) |
| Silent status=completed | Finish Experience |
| Bare “Done” with no beat | Session complete |

Legacy “Сегодня / Сделано / Почему сейчас” from mvp/next may remain as Session copy where useful, but the **entity** is Session, not “Today booklet”.

---

## Hierarchy (user-facing)

```text
Guide
  ├── Cover
  ├── Identity
  └── Cycles
        └── Sessions          (atoms: one opening each)
              └── UI Blocks
```

User mostly touches Guide + Session. Cover/Identity/Focus are felt on Continue and Guide. Cycles/Blocks are felt, not necessarily named everywhere.
