# 05 — Screens

Page inventory for Facio 0.1. Each screen has **one job**.

---

## 1. Continue (Home)

**Job:** Show Focus-ranked ready Sessions; answer *which one now?*; one tap into Execute.

**Contains:**

- **Focus** Session first (Focus Engine)
- Session cards: **Cover** + UI Block type + short status + optional reason chip (*Overdue*, *5 min*, *Last day*)
- FAB `+` → Create
- Entry to Guides drawer
- Optional Morning Summary gate (aligned with same Focus Engine)

**Does not contain:** full roadmaps, chat, settings dump, archive as primary content, arbitrary sort.

**Empty state:** short prompt + Create (*What do you want?*).

---

## 2. Create (Intent)

**Job:** Capture Intent with minimal chrome.

**Contains:**

- One large field: *What do you want?*
- Optional example chips (scenario wedge)
- Submit → clarify / generate pipeline

**Does not contain:** project templates gallery as the main path; “New Project” wording.

---

## 3. Guide (Explore / trust)

**Job:** Answer *Why and where?* Beautifully. Enable Commitment and later orientation.

**Contains:**

- **Cover** (emoji/mark, title, difficulty, duration summary)
- Result / outcome
- Duration, difficulty / horizon (human-readable)
- Success definition (**finite end**)
- **Identity** (post-Commitment): started, progress bar, streak, completed / repaired / skipped
- **Roadmap** of Cycles / days / major Sessions (not a flat task dump)
- Clarify / edit while exploring (batch questions + comment as needed)
- Primary CTA:
  - pre-commit: **Start Guide**
  - post-commit: **Start Session** / Continue current Session when applicable
- Access to Repair / AI Edit / manual structure edit (always via Diff + Undo)
- Archive / abandon (secondary)

**Visual bar:** Cover + roadmap / journey — not spreadsheet PathList. User should grasp the whole path in ~5 seconds.

**Progressive content:** map and narrative can appear before live UI Block payloads; badges/hints for upcoming Block types are OK.

**Does not contain:** live Timer/Stepper as the hero of the whole Guide (those belong in Session).

---

## 4. Commitment (may be a state of Guide, not a separate route)

**Job:** Explicit contract to activate the Guide.

Show clearly:

- what you will get
- how long it takes
- what counts as success
- first Cycle shape

CTA: **Start Guide** → Guide becomes active → first Session appears on Continue / can open Session.

May be the bottom of the Guide page (preferred) rather than a duplicate full-map screen.

---

## 5. Session (Execute)

**Job:** Answer *What now?* with executable UI Blocks. Maximize doability.

**Layout direction (from prototype Session Stage — keep spirit):**

- UI Block stage as visual hero (~2/3)
- Short support: title / “now” line
- Done / Skip / Repair entry as secondary chrome
- Affordance to open Guide (swipe up + ≡)

**Contains:** only the current Session’s Blocks + completion controls.

**On complete:** **Session complete** beat (progress resolve + copy + brief celebration) → then Continue / next Focus.  
Session is an **atom** — one opening; see [11 §2–3](./11-success-systems.md).

**Does not contain:** entire Cycle list as the main scroll body; chat; multi-Guide switcher as the center; Identity stats as the hero.

---

## 6. Guides drawer

**Job:** Index of Guides + Archive + Settings entry.

Each row uses **Cover** (mark + title + duration/progress glance).  
Selecting a Guide → Guide screen (Identity + roadmap).

---

## 7. Morning Summary (optional sheet / interstitial)

**Job:** Brief yesterday → today focus when there is something to say.

CTA → Continue or deep-link today’s focus Session.

Skip if no signal.

---

## 8. Repair sheet

**Job:** Fast mutation when life breaks the plan — **never magic**.

Always:

1. Choose intent (+ reason / comment)
2. Show **Diff** (before → after)
3. Confirm → apply
4. Offer **Undo**

Minimum intents (evolve by domain): shift / lighten / rest / free-text reason — cook vs fitness differ.

---

## 9. Edit / AI Edit

**Job:** Change Guide structure or Session content without chat-home.

Entry: floating pencil or Guide overflow.

Modes: manual, AI edit, Repair, structure.

**Always:** Diff preview + Undo after apply.

---

## 10. Finish Experience

**Job:** Close the Guide as a finished story — not a silent `completed` flag.

```text
🎉 You did it.
{result}
{duration}
{N} Sessions · {R} Repairs · {S} skipped

[ Repeat ]     [ Start next Guide ]
```

Then archive / drawer. Stats from Identity.

---

## 11. Session complete (beat)

Transient end state of Session screen (or short interstitial): progress full + **Session complete** + brief celebration → Continue.

---

## 12. Settings / Archive

Secondary. Archive lists inactive Guides **with Cover**. Settings for locale, notifications, etc.

---

## Explicitly not a primary screen

| Screen | Status |
|--------|--------|
| Chat home | Forbidden |
| Instant Answer as product branch | Out of 0.1 primary (demote/remove) |
| Separate Accept with full map duplicate | Forbidden |
| Projects list as root | Replaced by Continue |
| Silent completion toast only | Forbidden — use Session complete + Finish Experience |

---

## Prototype → screen mapping

| Prototype screen | Facio 0.1 |
|------------------|-----------|
| `ProjectsScreen` | Continue (+ drawer absorbs list role) + Focus Engine |
| `IntentScreen` | Create |
| `InstantAnswerScreen` | Remove / non-primary |
| `DraftStudioScreen` | Fold into Guide Explore + Commitment |
| `ProjectHomeScreen` | Session (+ Session complete beat) |
| `PathScreen` | Guide (Cover + Identity + roadmap) |
| `HistoryScreen` | Archive section |
| Repair / FinishCycle / NextCycle sheets | Repair **with Diff+Undo**; Finish Experience for Guide end; next cycle stays for mid-Guide chapters |
