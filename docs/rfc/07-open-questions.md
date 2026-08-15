# 07 — Open questions

Do not invent these in implementation. Default until decided: the conservative column.

**Locked in v0.7 (new centre):** the assistant **supplies the method** (“I don’t know how” is the entry point) and materialising it once is the entry, not the product; the product carries **reason + cadence + drift** in one object ([00](./00-vision.md)); **Subject** is the centre of the model, with `cadence`, `window`, `cues`, derived `drift` ([04](./04-domain-model.md)); a **Cue** is a fact with a required `surface` and a traceable `origin`; drift triggers the morning card and **must offer to shrink, never to try harder** (P8); breadth of subjects is free, depth in a runtime waits for phase 3 (P13); the wedge cases are push-ups, bike, vegetables, a project step — **cooking is phase 3, not the wedge**.

**Still locked from v0.6:** lid over pan; one vertical feed (tabs parked); composer resumes current chat + **New chat**; kebab → widget’s chat + instance carousel; Use ≠ Inspect; centered snapshots; P3; no Episode; P10 Today-first; P15 gestures; Deeds; specialists (Hevy / YouTube) named in [00](./00-vision.md); memory measured by hit rate.

**Changed in v0.7 — do not read the old wording:** P8 now triggers on **delta or drift** and escalation across cadence periods is allowed (v0.6 said “ignore → do not escalate”). P10 now distinguishes empty-because-nothing-committed from empty-because-drifting (v0.6 allowed both silently). P13 is persistence, not vertical depth. Never-do #14 is about missing cadence/cue/drift, not about which types ship.

| ID | Question | Conservative default |
|----|----------|----------------------|
| Q1 | Exact v1 widget catalog | Counter, checklist, tick-with-cadence, reminder, timer. Stepper if a subject needs beats. **Timeline is phase 3.** Every type carries cadence + do-time cues + drift, or it does not ship ([02 P13](./02-principles.md)). |
| Q2 | User rearrange | Complete / dismiss / postpone. No layout editor. |
| Q3 | Threads | **Locked:** current chat resumes. New chat explicit. Pan Talks lists the rest. |
| Q4 | Where it *runs* | **Locked:** Use vs Inspect. |
| Q5 | Rank | **Locked v0** inside non-empty Today. |
| Q6 | Morning placement | Today tile. Absent only if there is **no delta and no drift**. |
| Q7 | Push | Timed reminders yes, fired inside the subject’s window. Morning notify only if there is a card — including a **drift** card. Generic win-back (“we miss you”) stays off; a drift ask about a subject the user created is not win-back (P8). |
| Q8 | Auto cues | Conclusions reached in talk, check-in remarks, explicit remember. Every cue needs a `surface`. No silent mining, and no cue applied without being shown. |
| Q9 | Reuse `archive/apps` | Runtimes maybe. Not IA / Plan Feed / Guide. |
| Q10 | Physical day | Honesty inside training widgets only. |
| Q11 | Clarify before first tiles | Short batch max. Place a draft tile, then talk. |
| Q12 | Identity / Cover / Finish | Out of v1. |
| Q13 | Monetization | **After free demand.** Never paywall a widget already on Today ([06](./06-never-do.md) #11), and never paywall a **cue or a reminder** — that is the product working, not a premium feature. Sketch: Free = real lid + composer + a few subjects; Plus = unlimited subjects, richer cues, deeper runtimes. No billing design in this pack. |
| Q14 | Voice | Slot to the right of composer; after the loop works. |
| Q15 | Gestures on lid tiles | **Locked:** no inner carousel on the lid. |
| Q16 | Horizontal category tabs | **Parked.** |
| Q17 | Kebab vs current chat if widget never appeared | Current chat + widget as send-context. |
| Q18 | Odd grid sizes and packing | Prefer `4×1` / `2×2` / `4×2` / `4×4`. Packing v0 in [03](./03-product.md): row-major in rank order, gaps allowed, no reflow. Revisit against a real week, not by adding a layout engine. |
| Q19 | Auth | Device-id was prototype-only. Real accounts before multi-device sync. Provider TBD. |
| Q20 | Source of truth / offline | **Server of record** for widget state (as archive 0.1). Lid **reads from cache** so execute works offline (P5). Mutations queue and sync. Conflict: last-write-wins on **structure** (payload, `version`). **Runtime progress is not LWW** — ticks, elapsed timers and stepper position merge per item, and a stale structural write must never drop them ([06](./06-never-do.md) AI #2). Plain LWW over the whole widget silently eats a set logged offline, which is P5 failing at exactly the moment it matters. Still not designed here. |
| Q21 | Reminder infra | OS local notification from the reminder object. Server fan-out later if local is not enough. No LLM at fire. |
| Q22 | Eval harness | Required before widening the tool loop (create / mutate / explain). Not optional polish. |
| Q23 | Delivery phases | Product wedge in [00](./00-vision.md). Eng: (1) subject + cadence + counter/tick + **cue shown at do-time**, local only (2) reminder with window (3) drift + morning card with shrink chips (4) chat tools + New chat (5) Deeds / Inspect carousel (6) server, auth, sync (7) measure cost/active day. Note the order: **cues and drift come before the chat plumbing**, because they are the product. |
| Q24 | Cost per active day | **Measure**; do not invent a USD number here. Gate Plus on a measured budget. Drift and reminders are arithmetic, so the cheap loop is most of the value. |
| Q25 | P3 leak boundary inside a long thread | One continuous chat (P2) makes “has a desk object” soft by construction: after the first binding, almost any question has an object in context. **No limiter in v0** — measure the share of turns that neither mutate, remember, nor explain a bound widget. Add a rule only if that share grows. Do not build a classifier up front. |
| Q26 | Cadence granularity | **Count per period** (`3×/week`), not fixed weekdays. Missing Tuesday must not read as failure; missing the count must. Fixed days only if a subject genuinely needs them (a class at 19:00) — and then it is a calendar event, not a cadence. |
| Q27 | Drift threshold | **One full cadence period missed** with zero instances. Weekly subject → 8 days of silence. Daily-ish → 3 days. The bike sat 21 days; anything under a week is already a win. Never more than one drift card at a time, even if three subjects drift — pick the oldest. |
| Q28 | Drift escalation ladder | Ask at most **once per cadence period**, same object, same volume. First ask: “move it to today?” Second: “once a week instead?” Third: “retire it?” After a retire offer is declined twice, **stop asking** and leave the subject in Deeds without a cadence. Escalation goes **down** in commitment, never up in volume ([06](./06-never-do.md) #21). |
| Q29 | Does this work for open-ended subjects? | **Assume no until dogfood says otherwise.** Push-ups, bike and vegetables are short, repeatable and verifiable. “Build the project” is open-ended, and “I abandon plans” is about will, not memory — the mechanic may simply not reach it. Default: model a project as a subject whose instances are **its next concrete step**, and expect this to be the case that fails first. Do not widen to projects because the physical three worked. |
| Q30 | Method quality when the assistant is the only coach | The founding case worked — 4 → 28 reps on an AI-designed progression — so the bar is “good enough to progress,” not “a trainer wrote it.” **Pain is a hard stop:** technique and a smaller number, never a bolder plan ([06](./06-never-do.md) safety #5). Open: whether generated methods need review on subjects touching health. Default until decided — ship them, log them, read the log. |
| Q31 | Select-a-phrase → cue | **Locked as the create path for clarifications:** select any span of assistant text → “what does this mean?” → answer to the user **and** a `clarification` cue on that step, `quote` stored as text. Open: whether the same gesture should also offer “remember this as a correction.” Default — no, one verb per gesture. |
| Q32 | A method delivered is not a method understood | New failure axis: the second founding case did not evaporate over time, it **never landed**. Default: one check after the first instance — “did that make sense, or should it be shown differently?” — plus a `?` on every step. Answer it with her own photo and a link, not with a sourced catalogue ([06](./06-never-do.md) #23). Measure: share of first instances that trigger a clarification request; if it is high, the method text is too terse, not the user too slow. |
| Q33 | Media on a cue | **Resolved by asking, not guessing.** The second user first asked for “a picture from the internet showing how the exercise is done.” The discriminating question was: do you need *an image*, or do you need *not to leave the app and search*? Answer: **video is enough.** So: **`link`, embedded in the step** — we host nothing, curate nothing, and no exercise catalogue is needed. `photo` (the user’s own) stays available for “which machine is mine.” **Parked, possibly forever:** sourced images, licensed exercise databases, generated diagrams — that road costs a canonical exercise catalogue and makes fitness the first deep vertical, against P13. At most one item per cue, riding that cue’s surface. Q20 note: a photo is the product’s first binary payload; blobs need local-first handling and last-write-wins must not silently replace one. |

## This pack is product, not an eng spec

Sync, auth, scheduler, eval, and unit economics **kill dates** if ignored — they are listed as Q19–Q24 with conservative defaults, not designed here. Do not grow this folder back into the archive 27-file architecture pack until the lid works on other people.

## The dogfood that decides this

The claim in [00](./00-vision.md) is testable on one person in two weeks, because that person already has the four subjects and already failed at three of them.

- **Subjects:** push-ups (`3×/week`, target 30, cue “brace core + glutes”), exercise bike (`2×/week`, window from “the gym shuts at 22”), vegetables (`daily-ish`), one project step.
- **Build:** subject + cadence + counter/tick + cue at do-time + reminder with window + drift card. Local storage. No server, no auth, no sync, no Deeds, no carousel, no chat plumbing beyond writing a cue by hand if needed.
- **Kill criteria, written before starting:** if after two weeks no cue was read at do-time when it mattered, or drift was never surfaced before the failure had already happened, the mechanic does not work and no amount of IA fixes it.

**A second user arrived on her own.** Same entry point, independently: photographed the gym machines, uploaded them to a chat, got exercise names and form notes — and did not understand what to actually do. Her plan is sitting in a chat thread right now and will evaporate on the same schedule.

- **What she tests that the author cannot:** a **beginner** who did not design her own method, whose failure is comprehension rather than decay, and who is not emotionally invested in the app existing.
- **Her subjects:** a gym day (`2×/week`), steps carrying `clarification` cues from her own selections, an **embedded video** behind the `?` on movements she is unsure of, and optionally her own photos of the machines. She photographed those machines before this product existed, unprompted, to ask a chat what to do with them — the strongest signal in this pack about what to build.
- **One requirement already checked with her, not assumed:** she asked for an image and, when asked what the image was *for*, said video was enough — Q33 above. Two guesses about her needs were wrong before that question got asked. Keep asking her instead of modelling her.
- **Extra risk:** a beginner on machines following generated form advice. Safety #5 binds harder here — anything that pulls or clicks gets less weight and technique, never another set.
- **What a pass still does not prove:** n=2, one of them the author and one of them family. It earns the right to find a stranger, not to build the server.

## Explicitly out of this RFC

Blueprint DSL, Intent Economy, Coach billing, social, “any intent,” specialist-grade Hevy clone, cooking as the wedge.

## What “done” means for this concept pack

Enough to implement **product** against when the locked list at the top holds.  
Not done: Q16, Q19–Q24 as real designs, Q26–Q29 as measured answers, visual polish, implementation tickets.
