# 04 — Domain model

```text
User
  └── Subject[]                   push-ups, bike, vegetables, project X — the centre
        ├── cadence               3×/week, daily-ish, 2×/week, none
        ├── window                when it can happen (gym shuts at 22 → by 19:00)
        ├── Cue[]                 facts that must surface at do-time
        ├── Instance[]            one occurrence — kebab carousel
        └── drift                 derived: cadence promised vs instances done
  └── Lid feed                    a view of what is due now, not a second inventory
        ├── Today widgets
        ├── Lifetime widgets
        ├── Soon widgets          (glance)
        └── Postponed widgets     (glance)
  └── Chat[]                      (pan Talks; one is current; may bind many widgets)
  └── Reminder[]                  fired from a subject’s cadence + window
```

No Episode / Guide entity. No bottom tabs. The lid is a **projection** of subjects due now — the subject is where the reason lives between occurrences.

---

## Lid

One vertical feed. Opening it never requires an LLM.

Invariants:

- **Today** is the first viewport (P10). Other sections may exist below.
- Idle completed plays leave Today.
- Rank v0 applies **inside Today**.
- Type owns tile size on a 4-column grid.

## Widget

| Field | Notes |
|-------|--------|
| id, type | catalog enum |
| title | |
| payload | items, beats, markers, … |
| status | ready / running / done / skipped / snoozed / archived |
| when | date/time / day slot |
| section | today / lifetime / soon / postponed |
| group_id | same intent burst; not a screen |
| subject_id | kebab / Deeds / thread |
| instance_id | carousel slot |
| tile_size | from type |
| version | live schema version (chat snapshots); **not** a carousel slot |

Invariants:

- Today/Lifetime: checklist/timer may be interactive on the tile; stepper is not.
- Soon/Postponed: not interactive; tap → Inspect.
- Done leaves Today unless waiting on morning confirm.
- A widget bound to a subject renders that subject’s `do-time` cues. Cues that exist and are not shown mean the widget is broken (P9).

## Subject — the centre of the model

A **subject** is a practice that recurs: `push-ups`, `exercise bike`, `vegetables`, `project X`.

| Field | Notes |
|-------|--------|
| id, title | the user’s words |
| cadence | `3×/week`, `daily-ish`, `2×/week`, `none` (one-off). A **count per period**, not fixed weekdays ([07](./07-open-questions.md) Q26) |
| window | when it can happen, derived from cues (“the gym shuts at 22” → fire by 19:00). **May hold several stated hours** (“10, 12, 15, 16:30…”) — one window with an ordered list, not one event per hour ([07](./07-open-questions.md) Q34) |
| cue_ids | facts that must surface at do-time, ordered |
| target | optional progression state (28 → 30 reps) |
| instance_ids | occurrences in time |
| status | active / shrunk / paused / retired |
| paused_at | set when `paused`; empty otherwise. Check-in fire = `paused_at` + 2 days (scheduler, not LLM) |

Invariants:

- **Cues surface on the widget at do-time**, never only in a subject settings screen (P9).
- **Drift is derived, never stored as a score:** promised cadence vs instances completed over a trailing period. No streak number, ever (P7).
- Cadence is a count per period, so missing Tuesday is not a failure — missing the *count* is.
- **A count above one inside a single period means that many occurrences that day**, each with its own instance and its own tile, completed separately ([07](./07-open-questions.md) Q34). Seven checks a day is seven ticks, not one tick pressed seven times — a widget already done cannot record the next check.
- `cadence: none` with no instances is not drift; it is a finished thing.
- Retiring or shrinking a subject keeps its instances and cues. Nothing is deleted as punishment.
- **Pause is not shrink and not retire.** Pain + a miss freezes the practice: cadence and target stay; usual reminders are silent; a one-shot local check-in asks «готов тренироваться?» after two days. Thaw only when the person says it let go. Pause does not raise volume.

**Instance** — one occurrence in time (Monday’s session, tonight’s ride). Carousel lists instances. `+` creates one. `z` is a prepared future one.

Schema versions of an instance belong in **conversation snapshots**, not as extra carousel days (except that a day’s *face* may have been v1 or v2 when that day ran).

## Cue — a fact with a job

A **cue** is a MemoryFact bound to a subject *and to a place where it appears*. This is the object the whole product exists for: it is what a conversation leaves behind.

| Field | Notes |
|-------|--------|
| subject_id | which practice |
| step_id | optional — the step or item it belongs to |
| kind | `correction` (changes how it is done) / `clarification` (explains a term) |
| text | “brace the core and the glutes”; or the explanation of a phrase the user selected |
| quote | the exact phrase the user selected, when the cue came from a selection |
| media | optional, **at most one**: `photo` (the user’s own) or `link` (a URL, usually a video) |
| origin | the chat turn — and the selection inside it — so the reason stays traceable |
| surface | `do-time` (inline on the widget) / `on-demand` (behind a `?` on that step) / `timing` (constrains the reminder) / `placement` (defaults for the next instance) |
| hits | times surfaced **and** applied |

Invariants:

- Every cue has a `surface`. A fact with nowhere to appear is not a cue, and storing it is P9 failure.
- **`correction` defaults to `do-time`; `clarification` defaults to `on-demand`.** Otherwise rep one becomes a wall of text and P9 dies by drowning. An explanation is looked up; a correction must be seen.
- `quote` is stored **as text**, not as an offset into a message. Anchors into a transcript dangle as soon as the method changes.
- A selection with no bound subject produces **no cue** — text only. No orphans.
- **`link` renders in place** — a player or preview inside the step, not a jump out to a browser. The requirement it satisfies is *do not make me leave and search*, so opening an external app fails it ([07](./07-open-questions.md) Q33).
- **`photo` is the user’s own picture** — her shot of that machine, that shelf, that piece of equipment. Free in every sense: no licensing, no sourcing, no curation. It answers “which one is mine,” which is a real question, though not the one that was asked for.
- **A step must be executable without its media.** Video needs network and gyms have bad signal; media is an on-demand extra, never a precondition for doing the thing (P5 in spirit).
- What stays forbidden is **sourcing or curating a library** of media ([06](./06-never-do.md) #23) — not one item on a cue.
- Media rides with the cue’s surface: a `clarification` video or photo sits behind the `?`, not inline at do-time. A thumbnail inline is allowed; an autoplaying player is not.
- `origin` is kept so “why do I do it this way?” returns the actual conversation.
- Cues are **shown**, not silently applied (never-do AI #2).

## Conversation (chat)

ChatGPT-style threads. One is **current**. Lid composer opens it. **New chat** archives current into pan Talks and starts empty. Collapse does not change current.

A chat may contain centered snapshots of **many** widgets. Kebab finds the chat that last bound this widget (else current) and scrolls to the instance chapter.

### Snapshot and chapter

A **snapshot** is a message — the centered card written when a widget is bound or structurally changed.

| Field | Notes |
|-------|--------|
| chat_id, message_id | position in the thread |
| widget_id | the bound object |
| subject_id, instance_id | which cook, which day |
| version | widget schema version at write time |

**Chapter is derived, not stored:** the snapshots of one `instance_id` inside one chat. “Scroll to the chapter” means scroll to the **latest** snapshot of that instance. Moving the carousel re-resolves the anchor inside the same chat; it does not open another chat.

There is no Chapter entity and no chapter the user is told about — it is a scroll target.

Invariants:

- Live state is not reconstructed from the transcript.
- Snapshots are not runtimes.
- Explain-only: no new card.
- Lid composer without New chat **resumes** current.
- An instance with no snapshot in that chat has no chapter; the miniature stays where it is (see [07](./07-open-questions.md) Q17).

## Reminder / Morning / Audit

**Reminder** — deterministic, fired from the subject’s cadence and window. No LLM at fire time (P5). The window is what makes it fire at 19:00 instead of 21:40.

**Morning** — deterministic snapshot; at most one question, triggered by delta **or drift** (P8). A drift question always carries a shrink option.

**Audit** — widget versions, tool calls, cue writes, cue hits. Hit rate is not measurable without it.

---

## Mapping from the old model

| Facio 0.1 / v0.3 | Now |
|------------------|-----|
| Guide / Episode | Subject + instances |
| MemoryFact (loose, by string) | **Cue** — subject + `surface` + `origin` |
| — | **Subject cadence, window, drift** (the new centre) |
| Session | Use fullscreen |
| Continue / desk tab | Lid feed |
| History tab | Pan Talks |
| Settings tab | Pan bottom |
| Plan Feed | Centered snapshots in a subject thread |
| Hero Preview | Lid tile |
| Focus Engine | Rank inside Today |
