# 02 — Principles

Binding rules. A feature that violates them needs an explicit exception in [07](./07-open-questions.md) or a revision of this file.

## P1 — The lid is home

The app opens on the **lid**: one vertical feed. Not a blank prompt. Not the pan. Not Guides.

## P2 — Chats like ChatGPT, doors onto the desk

One assistant, not Manual / Feed / Repair as parallel homes. People already know: a chat continues until **New chat**.

- **Lid composer** — opens the **current chat**. Collapse hides the sheet; it does not start a new thread. Re-tap resumes.
- **New chat** — control at the **top of the sheet**. Archives the current chat into the pan (Talks) and starts empty. This is the only “reset.”
- **Kebab** — opens the chat that last bound this widget (or the current chat if it already has it), miniature scrolled to that instance chapter.

Voice later uses the same composer slot (button to the right of the input).

## P3 — Talk is grounded in the desk

A turn must be **about the desk or the found widget**. It does **not** have to write schema or memory.

Legal outcomes: **mutate** / **remember** / **understand** (“what is brisket?”).  
No desk object → leak. Do not force a patch after an explanation.

## P4 — Closed, executable widgets

Client-owned catalog. LLM fills schema; client renders and runs. Type owns tile size. No freeform UI. No user home-screen layout editor.

## P5 — Daily loop without LLM

Opening the lid, ticking Today/Lifetime checkboxes, running a timer, firing a reminder: no model.

## P6 — Visible mutation, reversible

Structural AI edits: live tile + new **centered** snapshot in that talk. Finger ticks on the lid do not spam the thread.

## P7 — User owns the desk

No hostage streaks, no shame, no “you’ll lose progress” as retention.

## P8 — Check-in is operational

Morning: deterministic snapshot + at most **one** question about **one** stalled object. No delta → no card. Ignore → do not escalate.

## P9 — Memory is a fact that hits next time

Hit rate (applied + shown), not count. No raw-chat RAG as v1. No silent mining.

## P10 — Today is the first viewport

**Few tiles ≠ few tasks.** A 12-item checklist is one body.

The lid is one feed, but **the first screen is Today** (plus at most a crumb of Lifetime). Soon / Postponed / extra Lifetime live **below the fold**. `more` is for those tails, **not** for Today.

**Empty Today is allowed.** Do not invent chores so D1 looks full. Off days (no cook, no train) are filled only by what the user put there: a short Today list, a Lifetime instrument they chose, or nothing. Opening Facio is not mandatory every calendar morning. Memory pays off on **subject repeat** (next carbonara), not on daily padding.

Rank v0 **inside Today** when it is non-empty: in progress → overdue → unanswered morning → soon by time → today incomplete.  
Streaks / short-win casino: not v0.

## P11 — Plays end; the desk does not

No Episode noun. Finished carbonara leaves Today. Find it later via pan → **Deeds** → kebab carousel (`+` to repeat). Standing instruments belong in **Lifetime**, not as fake infinity of a cook.

## P12 — Cost is a product feature

No pep-push into silence. Voice and win-back after the core loop. There is **no dollar figure** in this product pack; implementation must measure cost per active day before Plus.

## P13 — Narrow excellence (product, not every day)

The **shipped catalog** must include executable wedge types (timeline, stepper, timer) — that is what never-do “no planner-only v1” means.

That does **not** mean Today is a cook every day. Episodes are episodic. P13 forbids a v1 *without* those types. It does not forbid a Today that is sometimes only a checklist the user asked for.

Do not add a third vertical until one of the two bars (carbonara / training day) holds against “I’ll just use YouTube / Hevy tonight.”

## P14 — Safety is not a sidebar

Health, minors, self-harm, medical: policy first.

## P15 — Gestures stay few

| Gesture | Where |
|---------|--------|
| Left **gutter** (~16–24 pt) | Slide lid → pan. Off when keyboard up. Off on fullscreen (there, left = back). |
| Vertical on chat sheet | Up expand / header down collapse |
| Horizontal | **Inspect** carousel only |
| Stepper Use | Bottom **buttons**, no swipe |

No horizontal paging of lid sections (tabs parked). No stage-carousel / stack-flip **on the lid**; instance history lives in the kebab.

Visible **☰** (or equivalent) also opens the pan. Edge-only is not enough.

## Checklist before shipping a surface

- [ ] Can the user act in under a minute without talking?
- [ ] Is Today obvious without scrolling a warehouse?
- [ ] New chat is visible at the top of the sheet; composer resume is not a trap without it?
- [ ] Use cannot swipe into another day?
- [ ] Chat cards are snapshots, centered, not runtimes?
- [ ] Return-to-desk and execution, not messages?
