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
14. **Never** ship widget types **without cadence, do-time cues and drift**. Checklist + reminder + calendar *with* those three is the product; the same types without them are a daily planner, and a weaker one ([02 P13](./02-principles.md)).
15. **Never** pad Today with **invented** chores so the lid is never empty. Surfacing a commitment the user made himself — including one he is behind on — is not padding ([02 P10](./02-principles.md)).
16. **Never** market the stepper/timeline as better than Hevy / cooking YouTube at their one job.
17. **Never** use Use-fullscreen horizontal swipe to change instance (Inspect only).
18. **Never** omit **New chat** at the top of the sheet (no way to reset except hunting the pan).
19. **Never** reveal the pan from Use/Inspect left-edge (that edge is back).
20. **Never** let a conclusion from a conversation exist only as text. If a turn produces something the user should do differently, it becomes a cue with a `surface`, a cadence, a window, or a target — or it was not a conclusion. This is the founding bug ([00](./00-vision.md)).
21. **Never** answer drift with “try harder.” A missed cadence is answered by an offer to move it, shrink it, or retire it ([02 P8](./02-principles.md)).
22. **Never** go silent about a subject the user is behind on. Three weeks of nothing is not politeness, it is the failure this product exists to fix.
23. **Never** source or curate a **library** of media, and never build a catalogue of canonical exercises to hang media on. That is a fitness app’s infrastructure, it serves one vertical, and it breaks the one-mechanic-many-subjects bet ([02 P13](./02-principles.md)). **Allowed and encouraged:** one item per cue — an **embedded video** rendered in the step, or the user’s **own photo**. Asked directly whether she needed an image or needed not to leave the app, the second user said video was enough ([07](./07-open-questions.md) Q33). Do not reopen this without new evidence.
24. **Never** let an explanation the user asked for stay only in the transcript. A selected phrase plus its answer becomes a `clarification` cue on that step ([05](./05-ai-and-memory.md)).

## AI / data

1. **Never** apply unvalidated model text as widget payload.
2. **Never** silently rewrite the desk (no visible change, no undo).
3. **Never** use a raw chat dump in a vector index as v1 memory.
4. **Never** index private intentions into a cross-user corpus.
5. **Never** train public models on private user content by default.
6. **Never** optimize for tokens, messages, or “time in chat.”
7. **Never** let the assistant bypass safety policy because it “has tools.”
8. **Never** force a schema patch after a grounded explanation.
9. **Never** store a fact without a `surface`. A fact with nowhere to appear is a note, and notes are the thing that already failed.
10. **Never** let the model compute drift or decide reminder timing. Cadence and window are arithmetic ([05](./05-ai-and-memory.md)).

## Safety / business

1. **Never** claim medical diagnosis, treatment, or guaranteed health outcomes.
2. **Never** target eating-disorder weight-loss behaviors; detect and deflect.
3. **Never** sell user intention or desk contents.
4. **Never** pretend to be a clinician or financial advisor.
5. **Never** raise a target or a cadence through reported pain. General technique and a smaller number, or nothing. “It hurts” is a boundary, not an input ([05](./05-ai-and-memory.md)).

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
| **Conclusion left in the transcript** | The founding bug; correct advice that evaporates |
| **Cue parked in a settings screen** | Nobody opens settings at rep one |
| **Sourced media library + exercise catalogue** | Licensing, wrong-image risk, and a whole vertical’s infrastructure. An embedded video was enough when asked |
| **Model-invented image URLs** | Hallucinated links, dead hotlinks, and a wrong picture on a movement is worse than none |
| **Media a step cannot run without** | Gyms have bad signal; the doing must not depend on the network |
| **Every clarification inline at do-time** | Rep one becomes a wall of text; P9 dies by drowning |
| **Types without cadence / cue / drift** | Weaker habit app; the reason is gone by week three |
| **Silence about a drifting subject** | The three-week bike — exactly what we exist to fix |
| **Streak number as the drift UI** | Guilt, and it hides the reason |
| **Fixed weekdays as cadence** | Missing Tuesday becomes a failure; count per period instead |
| Pad Today with **invented** chores | Fake planner; a commitment he made is not padding |
| “We beat Hevy at sets” | Ten shallow apps; lose the specialist user on day one |
| Daily AI pep / nagging morning | Cost + fatigue + shame |
| Repair as a special mode | Check-in + talk |
| Voice as v1 | Core loop unproven |
| RAG as magic personalization | Invisible, unused facts |
| Episode / Guide resurrection | Shell people must learn |
| One mega-goal for life | Junk drawer; plays must end |

If a stakeholder wants one of the above, the answer is no unless this file changes.
