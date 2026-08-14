# Facio — Product RFC (compact)

> Working title: **Facio** (repo: `fasio`)  
> Status: Draft RFC v0.6  
> Audience: founders, product, engineering  
> Goal: single source of truth **before** implementation of the rewrite

This pack replaces the archive Outcome-OS RFC as day-to-day product truth.  
Historical design: [`../../archive/docs/RFC/`](../../archive/docs/RFC/README.md) — reference only.

---

## What this is

Facio is a **lifelong daily assistant**. Home is a **lid** (крышка): one vertical feed of widget tiles. Chat history sits in a **pan** (сковородка) under the lid, revealed from the left edge. Cooking and training are projections on that lid, not a second product.

Three scales of the same object:

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

**Facio is a personal desk:** a lid of executable widgets for today (and a short lifetime row), plus ChatGPT-style chats that can read and change that desk.

---

## Critical stance (read this first)

1. **The lid is home.** Not a prompt, not a chat tab, not a list of Guides. The pan is an archive under the lid, not a second home.
2. **Neighbors are planners *and* specialists.** Beat Sunsama by running, not scheduling. Do **not** promise to beat Hevy or YouTube at their one screen. The spoken answer to “why not Hevy + Notes?” is in [00](./00-vision.md).
3. **Empty Today is allowed.** P10 is viewport, not “invent chores so the lid is never empty.” P13 is “ship executable types,” not “cook every day.”
4. **Lid composer resumes the current chat** (collapse hides the sheet). **New chat** is an explicit control at the top of the sheet, as in ChatGPT. Garlic then “call mom” stay in one thread until the user starts a new chat. Kebab jumps to the chat that last touched that widget.
5. **Talk is grounded in the desk** (mutate, remember, or explain). Chat cards are snapshots, centered. Runtime lives on the lid / Use fullscreen.
6. **Carousel = instances in time** (Tuesday’s workout, last carbonara). **Chat cards = versions of one instance** (added garlic tonight).
7. **Use ≠ Inspect.** Doing now vs browsing days. Do not swipe into yesterday mid-set.
8. **No Episode / Guide noun.** `group_id` + subject + instance carousel.
9. **Category tabs / horizontal paging of the lid are parked.** The lid is one vertical feed for now.

---

## Naming

Product: **Facio**. Repo may stay `fasio`.  
User-facing: **lid / desk**, **widget**, **assistant**. Internal metaphor: lid over pan.  
Do **not** ship Guide, Continue, Session, Path, Episode, or bottom **History | Desk | Settings** tabs.
