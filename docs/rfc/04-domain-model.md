# 04 — Domain model

```text
User
  └── Lid feed
        ├── Today widgets
        ├── Lifetime widgets
        ├── Soon widgets          (glance)
        └── Postponed widgets     (glance)
  └── Subject[]                   (carbonara, training, …)  — Deeds / memory, not Episode
        └── Instance[]            (a day, a cook)  — kebab carousel
  └── Chat[]                      (pan Talks; one is current; may bind many widgets)
  └── MemoryFact[]
  └── Reminder[]
```

No Episode / Guide entity. No bottom tabs.

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

## Subject and instance

**Subject** — stable identity for Deeds and memory (`carbonara`, `training`).  
**Instance** — one occurrence in time (Monday session, tonight’s cook). Carousel lists instances. `+` on carbonara creates an instance. `z` on training is future instances.

Schema versions of an instance belong in **conversation snapshots**, not as extra carousel days (except that a day’s *face* may have been v1 or v2 when that day ran).

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

## Reminder / MemoryFact / Morning / Audit

Same as v0.3: deterministic reminders; MemoryFact by `subject` string; morning snapshot + optional one question; audit for versions, tools, facts.

---

## Mapping from the old model

| Facio 0.1 / v0.3 | Now |
|------------------|-----|
| Guide / Episode | Subject + instances |
| Session | Use fullscreen |
| Continue / desk tab | Lid feed |
| History tab | Pan Talks |
| Settings tab | Pan bottom |
| Plan Feed | Centered snapshots in a subject thread |
| Hero Preview | Lid tile |
| Focus Engine | Rank inside Today |
