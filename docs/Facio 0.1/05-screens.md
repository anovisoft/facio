# 05 — Screens

Page inventory for Facio 0.1. Each screen has **one job**.

---

## 1. Continue (Home)

**Job:** Attention stack / workspace — Focus-ranked Sessions that need action **now**; one tap into Execute.

**Contains:**

- **Focus** Session first (Focus Engine)
- Large **Hero Preview** cards (Session as object): fragment of Block state + ~duration + optional reason chip (*Overdue*, *5 min*, *Last day*). Guide emoji may appear as context mark — card is still about the Session, not Guide Cover twin
- Only Sessions requiring attention (executable / overdue) — idle Guides stay in drawer
- FAB `+` → Create
- Entry to Guides drawer (compact inventory)
- Optional Morning Summary gate (aligned with same Focus Engine)

**Does not contain:** full roadmaps, Guide-Cover twin cards, interactive Full Block, idle Guides, chat, settings dump, archive as primary content, arbitrary sort.

**Empty state:** short prompt + Create (*What do you want?*).

Presentations: [11 §9](./11-success-systems.md).

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
- Pre-commit Explore is a **Plan Feed** ([15](./15-edit-surfaces.md)): sense → questions → versioned plan cards + free-form; **Manual** on tools of a card
- Primary CTA:
  - pre-commit: **Start Guide** on each plan card (no sticky page-bottom Accept)
  - post-commit: **Start Session** / Continue current Session when applicable
- Post-commit rebuild: Manual + Micro + AI Feed (Diff on AI apply) — not Session Execute chrome
- Archive / abandon (secondary)

**Visual bar:** Cover + roadmap of **Compact Summaries** — not spreadsheet PathList, not stacked Full Blocks. User should grasp the whole path in ~5 seconds.

**Progressive content:** map and narrative can appear before live UI Block payloads; Compact Summaries / badges OK before plugins materialize.

**Does not contain:** Full Block execute as the Guide hero (that belongs in Session); Hero Preview stack (that belongs on Continue).

---

## 4. Commitment (CTA on plan card — not a separate Accept screen)

**Job:** Explicit contract to activate the Guide from a chosen plan version.

Show clearly on the plan card (and its expand):

- what you will get
- how long it takes
- what counts as success
- first Cycle shape / roadmap

CTA: **Start Guide** on that card → Guide becomes active → first Session on Continue.  
No second full-map Accept screen; no sticky page-bottom Start competing with cards.

---

## 5. Session (Execute)

**Job:** Answer *How do I do it?* with **Full Block** execute. Maximize doability.

**Layout direction (Session chrome lock — PO 2026-08-04):**

- **Full Block** stage as visual hero (~2/3) — interactive
- Short support: title / day N/M when multi-day
- Sticky footer by Guide shape (`horizon_days`):
  - **Same-day** (`horizon_days === 1`): **Back** + **Next**; last step of the day → **Back** + **Done**
  - **Daily** (`horizon_days > 1`): one **Done**
- Header: back **‹** only (no “Continue” title); right **kebab** (not burger)
- Kebab: Full Guide · Edit Session → Manual / AI Feed · Postpone (micro) · Skip (micro) · Finish cycle (if allowed) · Archive
- AI Repair / lighten / rest — **not** on Session happy path; they seed **Active AI Feed** ([15](./15-edit-surfaces.md))

**Contains:** only the current Session’s Full Block(s) + completion chrome above.

**On complete:** intermediate same-day **Next** → complete → next Session (toast, no modal). **Done** (daily or last same-day) → always-on “Finish session?” assurance → Continue when no next Session.  
Session is an **atom** — one opening; see [11 §2–3](./11-success-systems.md).

**Does not contain:** entire Cycle list as the main scroll body; chat; multi-Guide switcher as the center; Identity stats as the hero; inline Repair CTA.

---

## 6. Guides drawer

**Job:** Compact **navigation inventory** — which paths am I on? (ChatGPT sidebar / Finder list — not a second Continue.)

Each row: emoji/mark + title (+ optional thin status). **Not** large Cover cards twinning Continue.  
All active Guides appear here (including idle / waiting). Archive + Settings entry in footer.

Selecting a Guide → Guide screen (Identity + roadmap with Compact Summaries).

---

## 7. Morning Summary (optional sheet / interstitial)

**Job:** Brief yesterday → today focus when there is something to say.

CTA → Continue or deep-link today’s focus Session.

Skip if no signal.

---

## 8. Plan Feed (Create Explore)

**Job:** Build the path as a versioned лента — not in-place overwrite, not chat-home.

Contains: user intent/replies, sense, **plan cards**, question batches, free-form composer.  
Each plan card: expandable roadmap + **Manual** tool edit + **Start Guide** CTA.  
AI may append a new plan card or only more questions. Canon: [15](./15-edit-surfaces.md).

---

## 9. Edit surfaces (Active) — Manual · Micro · AI Feed

**Job:** Rebuild a living Guide without leaving Execute as the daily home.

| Mechanic | Job |
|----------|-----|
| **Manual** | Edit all UI Block tools + structure (shared with Create) |
| **Micro-edits** | Skip / postpone — deterministic chrome |
| **AI Feed** | Repair лента; apply proposal → **Diff** → Undo |

Entry: Session kebab Edit Session; Guide Edit plan. Diff sheet is a **step**, not a peer product screen.

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
| `DraftStudioScreen` | **Plan Feed** Create Explore + Manual; Commitment CTA on plan card |
| `ProjectHomeScreen` | Session (+ Session complete beat); Edit → Manual / AI Feed |
| `PathScreen` | Guide (Cover + Identity + roadmap) |
| `HistoryScreen` | Archive section |
| Repair / FinishCycle / NextCycle sheets | Active **AI Feed** + Diff+Undo; Finish Experience for Guide end; next cycle mid-Guide |
