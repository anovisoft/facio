# 04 — Information architecture

## Three modes

```text
1. Create     “I want…”
2. Guide      “Show me the whole path.”   (Explore / trust)
3. Session    “Lead me now.”              (Execute)
```

Plus **Continue** — the default home / attention stack after the user has active Guides.

One-line product stack:

```text
Guide     → path (strategy)
Continue  → focus (tactics)
Session   → execution (operations)
```

The user chooses when to move from understand → do.

---

## Navigation depth

Intentionally short:

```text
Continue  (workspace — Hero Preview stack)
   ↓ open a Session card
Session   (Full Block execute)
   ↓ swipe up / ≡ / affordance
Guide     (roadmap — Compact Summaries)
```

Create is entered from Continue FAB (`+`) or empty state.  
Guides index is a **drawer** (ChatGPT-style under-sheet) — **compact navigation inventory**, not the home and not a twin of Continue.

---

## Home = Continue (workspace)

Shows **Focus-ranked Sessions that need attention now** (attention queue — not every active Guide). First card = **Focus** (Focus Engine).

Each card is a **Hero Preview** of the current Session (fragment of real action), not a Guide-Cover twin and not Full Block.

Example:

```text
🍝 Carbonara                    ← Focus · Last day
   Купить продукты
   ☐ Бекон  ☐ Яйца  ☑ Пармезан
   ≈10 мин
────────────────
🏋️ Push-ups
   Set 1 / 4 · 20 reps
   ≈15 мин
```

Guides with nothing to do today (waiting / next unlock tomorrow) stay in the **drawer only** — not on Continue.

FAB `+` bottom-right → Create.

**Not on Continue:** full Guide maps, idle Guides, archive browsing, chat, news, marketing widgets, unsorted dump by `updated_at`, interactive Full Block execute.

Ordering rules: [11 §1 Focus Engine](./11-success-systems.md).  
Presentations: [11 §9](./11-success-systems.md).

---

## Guide is always a first-class page

Every Guide has a full page — **beautiful roadmap**, not a dense PathList.

Job: trust and orientation in ≤ ~5 seconds.  
Roadmap rows use **Compact Summary** per Session (many Sessions → each stays small). Cover + Identity live here — not as twin cards on Continue.

Example skeleton:

```text
🍝 Carbonara

Result
✓ Cook authentic carbonara

Duration · Difficulty
1 session · Easy

──────────────
Path map (roadmap — Compact Summaries)
Day 1  ☑ Купить продукты
Day 1  ○ Готовить
or Cycle 1 → days → Cycle 2 → Complete

Progress
0%

[ Start Guide ]     ← pre-Commitment
or
[ Start Session ]   ← if already committed and Session ready
```

Pre-Commitment: Explore + edit + Start Guide.  
Post-Commitment: user rarely *needs* this daily, but it must stay one gesture away.

### Access to Guide from Session

- **Primary gesture (target):** swipe up on Session → Guide; swipe down → back to Session  
- **Explicit affordance:** ≡ or “path” control (discoverability; do not rely on swipe alone)

Guide is never “gone” after Start — it stopped being the homepage.

---

## Session is the execute surface

On open: **only the current Session** + its **Full Block** (interactive) → **Session complete** beat.  
This is not Hero Preview — full execute lives only here.

Examples:

```text
Workout · Stepper · Rest timer · Counter · Session complete
Cooking · Timeline · Checklist · Timer · Session complete
Shopping · Checklist · Session complete
Language · Flashcards · Session complete
```

Support text (title / “now”) is secondary to the Block stage.  
One opening per Session atom — [11 §3](./11-success-systems.md).

Full Guide is not the body of this screen.

---

## Guides drawer

Swipe from left or button:

```text
Guides
🍝 Carbonara     Easy · 25 min
🏋️ 30 Push-ups   14 days · ███░
🇬🇧 English A1    …
────────
Archive
Settings
```

Per Guide: **Cover** + Identity glance (progress / cycle day / last activity).

Selecting a Guide opens the **Guide page** (not auto-dump into Session unless that is the only sensible action).

---

## Create

After `+`:

```text
What do you want?
____________________
```

Then AI clarify → Guide generation → user explores Guide → Commitment.

See [06](./06-ux-flows.md).

---

## Morning Summary (should)

Each morning, if something changed:

```text
Yesterday: Completed / Skipped / Needs Repair
Today's Focus
[ Continue ]
```

If nothing changed — do not show.

---

## Edit entry points

Floating pencil (or equivalent) on Guide / Session chrome:

- Manual edit
- AI Edit
- Repair
- Structure change

Repair also via “Something changed?” / overflow — always fast.

---

## What this replaces in the prototype IA

| Prototype | Facio 0.1 |
|-----------|-----------|
| Root = Projects list | Root = **Continue** |
| ProjectHome = Session Stage of one project | **Session** screen (per Session); multi-Guide via Continue |
| Path via burger (secondary list) | **Guide** page as trust/roadmap peer |
| DraftStudio as main pre-start | Create → Guide Explore → Commitment |
| Instant Answer branch | Out of primary product (see scope) |

Runtime engine (cycles, plugins, physical day, repair, next cycle) stays under this IA.
