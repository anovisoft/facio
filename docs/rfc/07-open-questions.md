# 07 — Open questions

Do not invent these in implementation. Default until decided: the conservative column.

**Locked in v0.6:** lid over pan; one vertical feed (tabs parked); composer resumes current chat + **New chat**; kebab → widget’s chat + instance carousel; Use ≠ Inspect; centered snapshots; P3; no Episode; P10 Today-first **and empty Today allowed**; P13 = catalog must include executable types, not “cook every day”; P15 gestures; Deeds; specialists (Hevy / YouTube) named in [00](./00-vision.md); morning snapshot + one question; memory hit rate.

| ID | Question | Conservative default |
|----|----------|----------------------|
| Q1 | Exact v1 widget catalog | Checklist, timer, timeline, stepper, counter, reminder. Calendar only *with* executable types. |
| Q2 | User rearrange | Complete / dismiss / postpone. No layout editor. |
| Q3 | Threads | **Locked:** current chat resumes. New chat explicit. Pan Talks lists the rest. |
| Q4 | Where it *runs* | **Locked:** Use vs Inspect. |
| Q5 | Rank | **Locked v0** inside non-empty Today. |
| Q6 | Morning placement | Today tile. Absent if no delta (including empty Today). |
| Q7 | Push | Timed reminders yes. Morning notify only if there is a card. Win-back off. |
| Q8 | Auto MemoryFacts | Remarks + explicit remember. No silent mining. |
| Q9 | Reuse `archive/apps` | Runtimes maybe. Not IA / Plan Feed / Guide. |
| Q10 | Physical day | Honesty inside training widgets only. |
| Q11 | Clarify before first tiles | Short batch max. Place a draft tile, then talk. |
| Q12 | Identity / Cover / Finish | Out of v1. |
| Q13 | Monetization | **After free demand.** Never paywall a widget already on Today ([06](./06-never-do.md) #11). Sketch: Free = real lid + composer + at least one executable type, caps on volume; Plus = full mechanics; Pro = specialized blueprints/minimaps when those exist — not “see the path.” No billing design in this pack. |
| Q14 | Voice | Slot to the right of composer; after the loop works. |
| Q15 | Gestures on lid tiles | **Locked:** no inner carousel on the lid. |
| Q16 | Horizontal category tabs | **Parked.** |
| Q17 | Kebab vs current chat if widget never appeared | Current chat + widget as send-context. |
| Q18 | Odd grid sizes and packing | Prefer `4×1` / `2×2` / `4×2` / `4×4`. Packing v0 in [03](./03-product.md): row-major in rank order, gaps allowed, no reflow. Revisit against a real week, not by adding a layout engine. |
| Q19 | Auth | Device-id was prototype-only. Real accounts before multi-device sync. Provider TBD. |
| Q20 | Source of truth / offline | **Server of record** for widget state (as archive 0.1). Lid **reads from cache** so execute works offline (P5). Mutations queue and sync. Conflict: last-write-wins on **structure** (payload, `version`). **Runtime progress is not LWW** — ticks, elapsed timers and stepper position merge per item, and a stale structural write must never drop them ([06](./06-never-do.md) AI #2). Plain LWW over the whole widget silently eats a set logged offline, which is P5 failing at exactly the moment it matters. Still not designed here. |
| Q21 | Reminder infra | OS local notification from the reminder object. Server fan-out later if local is not enough. No LLM at fire. |
| Q22 | Eval harness | Required before widening the tool loop (create / mutate / explain). Not optional polish. |
| Q23 | Delivery phases | Product wedge in [00](./00-vision.md). Eng: (1) lid + catalog + cache execute (2) chat tools + New chat (3) reminders + morning (4) Deeds/Inspect carousel (5) measure cost/active day, then any Plus talk. |
| Q24 | Cost per active day | **Measure**; do not invent a USD number here. Gate Plus on a measured budget. |
| Q25 | P3 leak boundary inside a long thread | One continuous chat (P2) makes “has a desk object” soft by construction: after the first binding, almost any question has an object in context. **No limiter in v0** — measure the share of turns that neither mutate, remember, nor explain a bound widget. Add a rule only if that share grows. Do not build a classifier up front. |

## This pack is product, not an eng spec

Sync, auth, scheduler, eval, and unit economics **kill dates** if ignored — they are listed as Q19–Q24 with conservative defaults, not designed here. Do not grow this folder back into the archive 27-file architecture pack until the lid works on other people.

## Explicitly out of this RFC

Blueprint DSL, Intent Economy, Coach billing, social, “any intent,” specialist-grade Hevy clone.

## What “done” means for this concept pack

Enough to implement **product** against when the locked list at the top holds.  
Not done: Q16, Q19–Q24 as real designs, visual polish, implementation tickets.
