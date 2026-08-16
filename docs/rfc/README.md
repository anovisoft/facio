# Facio — Product RFC (compact)

> Working title: **Facio** (repo: `fasio`)  
> Status: Draft RFC v0.7  
> Audience: founders, product, engineering  
> Goal: single source of truth **before** implementation of the rewrite

This pack replaces the archive Outcome-OS RFC as day-to-day product truth.  
Historical design: [`../../archive/docs/RFC/`](../../archive/docs/RFC/README.md) — reference only.  
Engineering status (stack, ladder, “where we are”): [`../state/`](../state/README.md). Do not grow this folder into an eng spec.

---

## What this is

Facio **gives advice a body.** You want something and do not know how; you ask; you get a real method — and then that method comes back by itself, on the right day, at an hour that still works, with its reason attached.

Materialising the answer once is the entry. Bringing it back with its reason is the product. Only the first would be an export button on somebody else’s chat.

Home is a **lid** (крышка): one vertical feed of widget tiles showing what is due now. Chat history sits in a **pan** (сковородка) under the lid, revealed from the left edge.

Three objects carry the product:

```text
Subject   → a practice that recurs: push-ups, bike, vegetables, project X
            cadence + window + cues + derived drift
Cue       → a fact with a place to appear: “brace core + glutes” at rep one
Widget    → the executable surface of one instance, on the lid
```

Three scales of a widget:

```text
Tile          → glance on the lid (+ light interaction in Today / Lifetime)
Chat card     → snapshot in a message, centered as the shared table
Fullscreen    → Use (do) or Inspect (browse instances)
```

---

## Read order

1. [00 — Vision](./00-vision.md)  
2. [01 — Philosophy](./01-philosophy.md)  
3. [02 — Principles](./02-principles.md)  
4. [03 — Product](./03-product.md) — lid, pan, feed, composer, kebab, two fullscreens  
5. [04 — Domain model](./04-domain-model.md)  
6. [05 — AI and memory](./05-ai-and-memory.md)  
7. [06 — Never do](./06-never-do.md)  
8. [07 — Open questions](./07-open-questions.md)  

---

## One-sentence product definition

**Facio is where an answer gets a body and comes back on time with its reason** — a lid of executable widgets fed by practices that keep their own pace, plus ChatGPT-style chats that supply the method and can change what is on the desk.

---

## The founding case (the whole pack in one story)

Push-ups: 4 reps, target 30. An AI gives a real progression. Week two the lower back takes the load; the AI gives a real fix — brace the core and the glutes. Now at 28 reps, **and that cue is forgotten on nearly every set.** The exercise bike waited three weeks, not refused, just forgotten until 21:40 with the gym shut. “More vegetables” never became anything at all.

Every piece of advice was correct. All of it evaporated. That is the product.

---

## Critical stance (read this first)

1. **Reason + cadence + drift live in one object.** Ship one alone and we lose: the reason alone is Notes, the cadence alone is a habit app, drift alone is a guilt badge.
2. **A conclusion left as text is a bug.** If a turn changes how you should do something, it becomes a cue with a `surface`, a cadence, a window, or a target ([06](./06-never-do.md) #20).
3. **The assistant supplies the method, not just the bookkeeping.** “I don’t know how” is the entry point. But materialising the answer once is only the entry — a product that stops there is an export button.
4. **Cues appear at do-time.** On the widget at rep one, or in the reminder firing at 19:00 instead of 21:40. Never in a settings screen.
5. **Silence about drift is a failure, not politeness.** Three weeks of nothing gets one card — and that card offers to **shrink** the commitment, never to try harder ([02 P8](./02-principles.md)).
6. **Pain is a boundary, not a parameter.** Technique and a smaller number, never a bolder plan ([06](./06-never-do.md) safety #5).
7. **Breadth of subjects is free; depth in a runtime is expensive.** Push-ups are a counter with a cue; vegetables are a tick with a cadence. Cooking timelines and specialist steppers are phase 3.
8. **The lid is home.** Not a prompt, not a chat tab. The pan is an archive under the lid, not a second home. **Deeds** is the list of practices and how each is holding.
9. **Lid composer resumes the current chat** (collapse hides the sheet). **New chat** is an explicit control at the top of the sheet, as in ChatGPT.
10. **Talk is grounded in the desk** (mutate, remember, or explain). Chat cards are snapshots, centered. Runtime lives on the lid / Use fullscreen.
11. **Carousel = instances in time.** **Chat cards = versions of one instance.**
12. **Use ≠ Inspect.** Doing now vs browsing days. Do not swipe into yesterday mid-set.
13. **No Episode / Guide noun.** Subject + instance + `group_id`.
14. **Category tabs / horizontal paging of the lid are parked.** The lid is one vertical feed for now.

---

## Naming

Product: **Facio**. Repo may stay `fasio`.  
User-facing: **lid / desk**, **widget**, **assistant**. Internal metaphor: lid over pan.  
Do **not** ship Guide, Continue, Session, Path, Episode, or bottom **History | Desk | Settings** tabs.
