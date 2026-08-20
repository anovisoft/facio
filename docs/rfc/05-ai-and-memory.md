# 05 — AI and memory

## Role of AI

The assistant sits on the other side of the desk. Internally it **reads and writes desk objects through tools** (MCP or equivalent). The user never hears “MCP.”

They hear a short confirmation, or an explanation. They see the live tile change when schema changes. In chat, a bound widget appears as a **centered** snapshot (shared table).

A **lid-composer open** resumes the **current chat**. **New chat** (top of sheet) starts empty.

```text
User utterance (current chat, unless New chat)
  → (policy)
  → model with tools
  → tool: list_desk / get_widget / get_subject / list_cues
  → maybe: create | update | complete | postpone | remind | remember
  → if mutated: live tile + centered snapshot in **this chat**
  → if explain-only: text, no new card
```

## The one pipeline that matters

Everything else in this file supports this. A conclusion reached in conversation must land somewhere with a clock on it:

```text
want            “I can do 4, I want 30” — and no idea how
  ↓
method          the assistant supplies the progression — this is why the loop starts
  ↓
talk            “my lower back is taking the load”
  ↓
conclusion      “brace the whole core and the glutes”
  ↓
cue             bound to subject `push-ups`, surface = do-time, origin = this turn
  ↓
mechanic        appears on the push-up widget at rep one, every session
  ↓
check-in        “did you hold the brace? how’s the back?”
  ↓
new cue         or a changed cadence / target
```

Same shape for time: “the gym shuts at 22” is a cue with `surface: timing`, so the bike reminder fires at 19:00 instead of 21:40. Same for pace: “30 in a row” is a `target`, and today’s number is derived, not remembered by the user.

**A turn that produces a conclusion and leaves it as text has failed**, even when the text was correct. That is the founding bug ([00](./00-vision.md)), and it is a never-do ([06](./06-never-do.md) product #20).

## When LLM is allowed

| Allowed | Examples |
|---------|----------|
| **Supply the method** — the part the user does not know | “I can do 4, I want 30 in a row — how?” → a real progression |
| Turn an intent into a subject **with a cadence** | “I want to ride the bike twice a week” |
| Place widgets from intent | “push-ups three times a week, I’m at 28 now” |
| Edit via talk | “make the target 30”, “drop the bike to once a week”, “mark it done” |
| **Write a cue from a conclusion** | “then brace the core and the glutes” → cue on `push-ups`, `surface: do-time` |
| **Derive a window from a fact** | “that gym shuts at 22” → the reminder fires by 19:00 |
| Explain the focused widget | “what does bracing actually mean?” |
| Clarify if it branches the widgets | “how many days a week?” — once |
| Morning question | one operational line on a stalled or **drifting** subject, carrying a shrink option |
| Rare messy repair | “I got sick, rebuild this week” |

Explain-only is success. Do not require a plan patch after a definition. An optional, dismissible follow-up is allowed; a forced next mutation is not.

**Method is the entry point, and it has one condition.** The assistant is where the *how* comes from — “I want this and don’t know how” is the reason a subject exists at all. But a method must land in the same turn as a cadence, a target, a cue or a window. A progression that stays in the transcript is the founding bug in a new coat ([06](./06-never-do.md) #20).

## Ask about a phrase, keep the answer

Select any span of the assistant’s text → **what does this mean?** → the answer goes to the user *and* is attached to the subject as a `clarification` cue, carrying the selected phrase as `quote`.

This closes the founding bug in its second form. “Explain-only is success” is true about not forcing a schema patch — but if the explanation itself stays in the transcript, it evaporates like everything else.

The second founding case: photograph the gym machines, get exercise names and form notes from a chat, **not understand “keep your chest up,”** ask, get a good answer — and lose it before the next visit. The method was delivered and never landed.

A selection is the strongest signal we will ever get about what needed remembering. It beats model inference, because the user pointed at it.

Defaults:

- `clarification` → `on-demand`, behind a `?` on that step. Never inline; rep one must stay readable (P9).
- `correction` → inline `do-time`.
- No bound subject → text only, no orphan cue.
- The answer may carry **one** media item: a link (usually a video), or the user’s own photo.

**Her photo is the feature, not our image library.** She already photographed the machines to ask the question — that picture, attached to that step, answers “which one is mine” better than anything we could source, and it costs nothing but an attachment. Sourcing or curating images per exercise stays out ([06](./06-never-do.md) #23); a picture on a cue does not.

It is sewn into the **subject and its step** — not into a Guide. That noun stays dead ([06](./06-never-do.md) #3).

**Pain is a boundary, not a parameter to optimise.** The founding case includes “my lower back is taking the load.” Naming general technique — brace the core, let the glutes carry some of it — is fine, and it is exactly what worked. Diagnosing is not, and neither is raising a target or a cadence *through* reported pain. When pain is reported: general technique, a plain “this is not medical advice,” and an offer to lower the number ([02 P14](./02-principles.md), [06](./06-never-do.md) safety #5).

## When LLM is forbidden

| Forbidden | Do this instead |
|-----------|-----------------|
| Render today-desk | persisted widgets |
| Tick, timer, stepper runtime | client (desk / fullscreen) |
| Run those runtimes inside a chat snapshot | snapshot is a picture |
| Fire reminder | scheduler |
| **Compute drift** | deterministic: cadence vs instances done |
| **Decide when a reminder fires** | cadence + window, deterministic |
| Rank “what’s on today” | P10 rules |
| Daily pep with no object | don’t send |
| **Shame, or answer drift with “try harder”** | offer to move, shrink, or retire (P8) |
| Freeform new widget types | product ships a type |
| New snapshot card on a finger tick | only structural / commanded changes |
| Open-ended chat with no desk object | out of product |

## Tools (conceptual)

- `list_desk`, `get_widget`
- `get_subject`, `set_cadence`, `shrink_subject`, `retire_subject`, `freeze_subject`, `thaw_subject`
- `create_widget`, `update_widget`, `archive_widget`
- `complete`, `skip`, `postpone`, `move_to_date`
- `set_reminder`
- `list_cues`, `add_cue` — `surface` is **required**; a cue with nowhere to appear is rejected

Patches must validate against schema. Unvalidated model text never becomes widget payload.

## Context the model sees

**The desk, the focused widget, and relevant facts** — not the entire life transcript.

Current thread, truncated. Old threads opened explicitly. Do not concatenate all chats as “memory.”

## Memory

v1 = **Cue** ([04](./04-domain-model.md)): a fact bound to a subject *and to a place where it appears*.

Write: a conclusion reached in talk, a check-in remark, an explicit “remember.”  
Read: at do-time on the widget, in the timing of the reminder, in the defaults of the next instance.

Product metric: **hit rate** (surfaced + applied), not facts stored. One cue that reaches the hands at rep one beats forty stored insights. A fact with no `surface` is not memory, it is a note — and notes are what already failed ([00](./00-vision.md)).

“It knows me” is a weeks-long accumulation of *hits* — cues, windows, targets, corrections — not day-0 friendship.

**Not v1:** embedding the full chat as memory. Later retrieval over *facts and notes* is allowed; raw PII dumps and cross-user corpora are not ([06](./06-never-do.md)).

## Cost

- Finger path: ~0 tokens.
- Talk: one turn + tools, bounded. Explain-only still costs; keep answers short (a few sentences, tied to the step).
- Morning: generate only the optional one question, and only if showing a card.
- **Drift detection is free** — cadence vs instances is arithmetic, no model. Only the wording of the one ask may cost a call.
- Inactive users: no pep-push and no “we miss you.” A **drift ask about a subject they created** is not a win-back — it is bounded by that subject’s own cadence period (P8).
- No hidden always-on coach loop.

## Voice (later)

Same tools, different mouth. After desk + chat work.

## Relationship to the old AI strategy

Keep: deterministic core, generative edge, no LLM on daily execute, validate patches, budget.

Drop as the center: blueprint compiler, 100k intents, Coach billing, Plan Feed as create UX, “every turn must PATCH.”

New center as of v0.7: **a conclusion becomes a cue with a surface, on a subject with a cadence.** Generation quality matters less than whether the conclusion comes back on time.

Create is: current chat → tools → tiles on the lid. Explain is: text beside a snapshot that did not need a new version. **New chat** is explicit. Kebab jumps to a chat, it does not replace New chat.
