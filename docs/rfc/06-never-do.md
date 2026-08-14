# 06 — Never do

Hard constraints. “Just this once” needs a written exception with an expiry.

## Product

1. **Never** make unbounded chat the home screen (the lid stays home; the pan is an archive of chats, not the first screen).
2. **Never** require an LLM to see today or to complete a widget that already exists.
3. **Never** ship Guide / Continue / Session / Path / **Episode** as nouns people must learn.
4. **Never** give every widget its own AI product (parallel Manual, Feed, Repair homes).
5. **Never** treat the transcript as source of truth for recipes, tasks, or schedules.
6. **Never** run the widget **runtime** inside a historical chat card (timers, per-item ticks, stepper beats).
7. **Never** append a chat snapshot for ordinary finger completions on the desk.
8. **Never** let the user layout tiles like an iOS home screen; type owns shape.
9. **Never** use guilt, shame, or hostage streaks as retention.
10. **Never** send motivational pushes or morning pep with no desk object.
11. **Never** lock today’s deterministic widgets behind a paywall.
12. **Never** market “any goal / full life OS” while the catalog is thin.
13. **Never** make the user hunt Talks to recover an object that belongs on the lid (use the tile or Deeds).
14. **Never** ship a v1 **catalog** that is only checklist + reminder + calendar (daily-planner trap). A given *day* may still be only a checklist the user asked for ([02 P13](./02-principles.md)).
15. **Never** pad Today with fake chores so the lid is never empty.
16. **Never** market the stepper/timeline as better than Hevy / cooking YouTube at their one job.
17. **Never** use Use-fullscreen horizontal swipe to change instance (Inspect only).
18. **Never** omit **New chat** at the top of the sheet (no way to reset except hunting the pan).
19. **Never** reveal the pan from Use/Inspect left-edge (that edge is back).

## AI / data

1. **Never** apply unvalidated model text as widget payload.
2. **Never** silently rewrite the desk (no visible change, no undo).
3. **Never** use a raw chat dump in a vector index as v1 memory.
4. **Never** index private intentions into a cross-user corpus.
5. **Never** train public models on private user content by default.
6. **Never** optimize for tokens, messages, or “time in chat.”
7. **Never** let the assistant bypass safety policy because it “has tools.”
8. **Never** force a schema patch after a grounded explanation.

## Safety / business

1. **Never** claim medical diagnosis, treatment, or guaranteed health outcomes.
2. **Never** target eating-disorder weight-loss behaviors; detect and deflect.
3. **Never** sell user intention or desk contents.
4. **Never** pretend to be a clinician or financial advisor.

## Attractive traps (anti-patterns)

| Trap | Why it fails |
|------|----------------|
| Blank-box home prompt | Trains chat, not doing |
| Pan as inbox / chat-home | Lid is home; pan is archive |
| Lid composer always starts a new chat | Fights ChatGPT literacy; New chat exists for that |
| No New chat control | One eternal thread, or pan-only reset |
| Use = Inspect | Swipe into yesterday mid-workout |
| Bottom History \| Desk \| Settings tabs | Replaced by lid + pan |
| Horizontal category tabs on the lid | Parked; lid is one feed |
| Widget construction kit | Facio 0.1 overload, new costume |
| Live mini-app in a chat bubble | Three truths; Plan Feed again |
| Essay plans on the desk | ChatGPT already does this |
| Checklist-only **catalog** v1 | Weaker Sunsama |
| Pad Today so it is never empty | Fake planner; memory never repeats a subject |
| “We beat Hevy at sets” | Ten shallow apps; lose the specialist user on day one |
| Daily AI pep / nagging morning | Cost + fatigue + shame |
| Repair as a special mode | Check-in + talk |
| Voice as v1 | Core loop unproven |
| RAG as magic personalization | Invisible, unused facts |
| Episode / Guide resurrection | Shell people must learn |
| One mega-goal for life | Junk drawer; plays must end |

If a stakeholder wants one of the above, the answer is no unless this file changes.
