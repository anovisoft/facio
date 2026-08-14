# 03 — Product

```text
Lid (крышка)   →  one vertical feed of tiles + docked composer
Pan  (сковородка) →  under the lid: Talks, Deeds, Settings
Talk           →  current chat from composer (New chat to reset); kebab jumps to that widget’s chat
Rhythm         →  reminders + morning check
```

No bottom tabs. Horizontal category tabs are **parked**.

---

## Lid over pan

Facio 0.1’s Guides-under-Continue, reused for **history**, not for objects.

```text
pan (only from lid root)              lid
┌─────────────┐                       ┌──────────────────────────┐
│ Talks       │                       │ ☰                         │
│ Deeds       │                       │  Сегодня …                 │
│             │                       │  Lifetime …                │
│ ⚙ Settings  │                       │  В ближайшее …             │
└─────────────┘                       │  Отложили …                │
                                      │ [  What belongs here?  🎤] │
                                      └──────────────────────────┘
         ← gutter ~16–24 pt
```

- Tiles are **not** edge-to-edge into the gutter. Gutter ≠ “90% of a widget.”
- Fullscreen Use/Inspect: left edge = **back to lid**, not pan.
- Keyboard open: pan gesture off.
- **Talks** — conversation list. Opening one opens that subject’s sheet (not a chat-home inbox).
- **Deeds** — subjects (Carbonara, Training). Opens the **same kebab inspector** (carousel of instances, `+` to repeat). Last week’s carbonara lives here, not on Today.
- **Settings** — bottom of the pan. Stats/achievements later.

Do not dump a second widget warehouse into the pan. Live objects: lid. Dead/repeatable subjects: Deeds.

---

## Lid feed (one scroll)

Four sections, **not** four homes:

| Section | On first viewport? | Tile behavior | Tap empty / header |
|---------|--------------------|---------------|---------------------|
| **Сегодня** | Yes | May be interactive (checkbox, timer). Stepper tile is **not** a live stepper | **Use** fullscreen |
| **Lifetime** | At most a crumb | Same as Today. Standing instruments with no end (not a cook that forgot to finish) | **Use** |
| **В ближайшее время** | Below the fold | Glance only | **Inspect** |
| **Отложили** | Below the fold | Glance only | **Inspect** |

`more` loads more in Soon / Postponed / Lifetime tail. **Today has no `more`.** If Today needs it, Today is too big.

Grid: 4 columns. Sizes are **width × height** in cells. Type picks one of: `4×1` (banner), `1×2`, `1×4`, `2×2`, `2×4`, `3×4`, `4×2`, `4×4`. Prefer iOS-like `4×1` / `2×2` / `4×2` / `4×4` when a type fits. User does not place wallpaper.

**Packing v0.** Fill row-major inside each section, in rank order ([02 P10](./02-principles.md)). A tile that does not fit the remaining width starts a new row and **leaves the gap**. Never reorder tiles to close a hole — rank order carries information, density does not. If the gaps look bad on a real week, change the type’s size, not the packer ([07](./07-open-questions.md) Q18).

Kebab on every tile (top-right).

**Off days.** Cook and train are episodic. If Today is empty, leave it empty — composer is still there; Soon may sit below. A user-asked Today checklist is valid furniture. Padding the grid so every morning looks busy is the planner trap and kills memory (salt never pays off if carbonara never repeats as itself).

---

## Composer (docked on the lid)

Always visible on the lid. Voice control to the **right** of the field — later; reserve the slot.

Tap field → **chat sheet almost fullscreen** (handle on top). **Resumes the current chat.** Placeholder on an empty chat: *What belongs on the table?* — not *Ask anything*.

**New chat** — button at the **top of the sheet** (ChatGPT literacy). Archives current into pan Talks and opens a blank thread. Collapse does **not** reset.

A chat may bind **several** widgets: garlic, then “call mom,” are two centered snapshots in one thread unless the user hit New chat. The model finds objects via tools.

Human bubbles **right**, assistant **left**, widget card **center** (shared table).

Day-0: empty **Сегодня**, chips above the composer (`today` / `dinner` / `gym`). First send must leave **tiles on the lid**, not only bubbles.

---

## Chat sheet

Same expansion from lid composer and from kebab miniature: almost fullscreen, handle to collapse. Top of the expanded sheet: **New chat**.

In the sheet, MCP/tools see the user’s widgets. When the model binds an object, it appends a **snapshot** card in the center. Structural change → new snapshot. Explain-only (“what is brisket?”) → text, no new card. Finger ticks on the lid → no card.

Snapshot is not a runtime (no timer, no per-item ticks, no stepper beats inside the bubble). Tap card → Use or Inspect as appropriate.

Chats are ChatGPT threads: one **current**, many in pan Talks. A single chat may mention many widgets. Kebab does not invent a second messenger: it opens the chat that last attached this widget, scrolled to that **instance chapter** ([04](./04-domain-model.md) — derived scroll target, not an entity). Carousel moves the chapter, not a different app.

---

## Kebab inspector

Not a fourth product. Time + life of the object + its talk.

```text
title
[ postpone ] [ delete ]

        date
   [x][ YYY ][z]     instance carousel
      [ Open ]

┌─────────────────────┐
│  3×4 chat miniature │  scrolled to this chapter
│                     │
│ [ input           ] │
└─────────────────────┘
```

- Tap input / tap miniature / swipe the chat region **up** → same almost-fullscreen sheet (expand animation). Header down → back to miniature.
- **Open** → **Inspect** fullscreen (not Use).

### Carousel = instances, not schema versions

Versions of one cook stay in the chat as snapshots. Carousel slots are **days / repeats**:

- **Training:** `[past days…][ YYY now ][z upcoming prepared]`. If day 1–2 were widget v1 and later v2, slots are `[v1][v1][v2]…[YYY][z]` — the face of that **day**, not a diff of tonight.
- **Carbonara:** past cooks in `x`; instead of `z`, **`+`** starts a new cook.

---

## Two fullscreens

**Use** — from Today / Lifetime (header, empty space, live timer, Start):

- Do it now. Date is quiet.
- **No** left–right carousel (must not skip to tomorrow mid-set).
- Stepper: **buttons at the bottom**.
- No chat on this page. Kebab can jump to inspector.
- Back → lid.

**Inspect** — from kebab **Open**, or tap Soon / Postponed:

- Browse instances. Date is loud.
- Swipe left–right through the carousel.
- Past and `z` are **not** today’s live run (no “cooking last Tuesday for real”).
- `+` creates a new instance.
- Chat miniature / sheet belongs here.

---

## Gesture lock

See [02 P15](./02-principles.md). Lid tiles have **no** inner horizontal carousel and **no** iOS-stack flip. Instance history is kebab/Inspect only.

---

## Widget catalog (seed)

| Widget | Typical use | Lid |
|--------|-------------|-----|
| Checklist | shopping, prep, daily tasks | may tick on Today/Lifetime |
| Timer / TimerStack | countdown | may run on Today/Lifetime |
| Timeline | cook | glance on lid; **Use** to run |
| Stepper | strength | banner / compact; **Use** to run (buttons) |
| Counter / Dose | target count | compact |
| Calendar event | time-bound | row |
| Reminder | fire at a time | row |

Calendar/reminder without timeline/stepper/timer in v1 = daily-planner trap.

Same-intent burst (shop + prep + cook) → `group_id`. Shown as neighboring tiles or one stack **later**; not a Guide screen. No flip-stack on the lid in v0.5.

---

## Morning and reminders

Reminders fire **deterministically**. Tap → lid (or Inspect of that object). No LLM at fire time.

Morning: only if the lid has a delta. **90% snapshot** (yesterday / today facts). At most **one** question, **one** stalled object, chips Yes / No / Move to today / Postpone + remark. No delta → no card. Ignore → do not escalate.

Prefer a Today tile; not a third home.

**Good:** “Carbonara still isn’t marked done — did you cook it?”

**Bad:** crush-the-day; streak shame; “how do you feel?”; asking a done widget; two questions; longer than the lid; judging the person; ceremony when yesterday and today are empty.

---

## Journeys

### Daily

```text
Open → lid (Today)
  → tick / timer on tile, or Use fullscreen
  → or composer (current chat) / kebab / New chat
  → leave
```

### Two turns in one chat (default)

```text
Composer → “add garlic to carbonara” → centered snapshot + live tile
  → collapse → composer again → same chat
  → “add call mom to today” → second centered snapshot in the same thread
New chat (top) → blank thread; garlic chat lives in pan Talks
Kebab on carbonara → that chat (or the one that last bound it), scrolled to the cook
```

### Repeat last week’s carbonara

```text
Pan → Deeds → Carbonara → carousel → +  (or Open to inspect, then +)
```

---

## What this replaces from Facio 0.1

| 0.1 | Now |
|-----|-----|
| Continue | Lid feed |
| Guides drawer | Pan: Talks + Deeds + Settings (not object inventory as home) |
| Session | Use fullscreen |
| Path / Guide | Inspect + kebab carousel |
| Plan Feed | Centered snapshots in a subject thread |
| Bottom tabs (v0.3 experiment) | Lid + pan. Category **tabs parked** |

Runtime inside widgets may be reused. IA / Plan Feed / Guide ontology may not.
