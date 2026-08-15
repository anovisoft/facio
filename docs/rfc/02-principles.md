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

**Drift detection and reminder timing are arithmetic too** — cadence vs instances done, window vs clock. The model may word the one morning ask; it never decides whether there is one.

## P6 — Visible mutation, reversible

Structural AI edits: live tile + new **centered** snapshot in that talk. Finger ticks on the lid do not spam the thread.

## P7 — User owns the desk

No hostage streaks, no shame, no “you’ll lose progress” as retention.

## P8 — Check-in is operational, and drift is a signal

Morning: deterministic snapshot + at most **one** question about **one** object. Two triggers:

- **Delta** — something moved yesterday, or is due today.
- **Drift** — a subject missed its own cadence. Three silent weeks on the bike is a **bug**, not politeness.

No delta and no drift → no card.

Ignoring an ask does not escalate *inside* one cadence period. After a full period has passed it may be asked again — same object, at most once, never louder.

**A drift ask must offer to shrink the commitment, not to try harder:** move it, drop the cadence to once a week, or retire the subject. That is how this stays out of the guilt business (P7) while still breaking the silence.

## P9 — A fact must reach the hands

A fact stored and never surfaced did not happen. Facts attached to a subject surface **at do-time**: on the widget, in *when* the reminder fires, in the next placement. Not in a settings screen, not only in the transcript.

“Brace the core and the glutes” belongs on the push-up widget at rep one. “The gym shuts at 22” belongs in the reminder firing at 19:00.

Hit rate (applied + shown), not count. No raw-chat RAG as v1. No silent mining.

## P10 — Today is the first viewport

**Few tiles ≠ few tasks.** A 12-item checklist is one body.

The lid is one feed, but **the first screen is Today** (plus at most a crumb of Lifetime). Soon / Postponed / extra Lifetime live **below the fold**. `more` is for those tails, **not** for Today.

**Two kinds of empty Today, and they are not the same thing.**

- Empty because nothing is committed today → **allowed**. Leave it empty; do not invent chores so D1 looks full.
- Empty while a subject is **behind its own cadence** → **must not stay silent**. That emptiness *is* the drift, and it is the exact failure this product exists for (the bike, three weeks). Surface it as one Today card (P8).

Surfacing a commitment the user made himself is not padding — never-do #15 is about **invented** chores. Opening Facio is not mandatory every calendar morning. Memory pays off on **subject repeat**, not on daily filler.

Rank v0 **inside Today** when it is non-empty: in progress → overdue → unanswered morning → **drift card** → soon by time → today incomplete.  
Streaks / short-win casino: not v0.

## P11 — Instances end; subjects do not

No Episode noun. A finished session leaves Today. Find it later via pan → **Deeds** → kebab carousel (`+` to repeat).

A subject with a cadence returns by design — that is the product, not fake infinity. Fake infinity is a one-off that forgot to finish. **Deeds** is the list of subjects with their cadence and how each is holding, not a graveyard.

## P12 — Cost is a product feature

No pep-push into silence, and no generic win-back. A **drift ask about a subject the user created** is neither: it is bounded by that subject’s cadence and it always offers to shrink (P8).

Drift detection itself is arithmetic, so the most valuable behaviour in the product is also the cheapest. Voice comes after the core loop. There is **no dollar figure** in this product pack; implementation must measure cost per active day before Plus.

## P13 — Persistence first, depth later

The bet is **staying power across subjects**, not depth inside one. A counter with a cue, a tick with a cadence, and a reminder with a window already beat every neighbor on reason + cadence + drift ([00](./00-vision.md)).

So the **shipped catalog** must carry **cadence, do-time cues and drift** on every type. That — not the presence of a timeline — is what “no planner-only v1” means (never-do #14).

Breadth of subjects is free: add one whenever the user has one. Depth in a runtime (cook timeline, specialist-grade stepper) waits for phase 3.

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
- [ ] **Do this subject’s cues appear where the hands are, not in a settings screen?**
- [ ] **If this subject went quiet for a full cadence period, would the user hear about it?**
- [ ] **Does the drift ask offer to shrink, and never to try harder?**
- [ ] New chat is visible at the top of the sheet; composer resume is not a trap without it?
- [ ] Use cannot swipe into another day?
- [ ] Chat cards are snapshots, centered, not runtimes?
- [ ] Return-to-desk and execution, not messages?
