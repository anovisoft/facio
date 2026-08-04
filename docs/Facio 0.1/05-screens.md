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
- Clarify / edit while exploring (batch questions + comment as needed)
- Primary CTA:
  - pre-commit: **Start Guide**
  - post-commit: **Start Session** / Continue current Session when applicable
- Access to Repair / AI Edit / manual structure edit (always via Diff + Undo)
- Archive / abandon (secondary)

**Visual bar:** Cover + roadmap of **Compact Summaries** — not spreadsheet PathList, not stacked Full Blocks. User should grasp the whole path in ~5 seconds.

**Progressive content:** map and narrative can appear before live UI Block payloads; Compact Summaries / badges OK before plugins materialize.

**Does not contain:** Full Block execute as the Guide hero (that belongs in Session); Hero Preview stack (that belongs on Continue).

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

**Job:** Answer *How do I do it?* with **Full Block** execute. Maximize doability.

**Layout direction (Session chrome lock — PO 2026-08-04):**

- **Full Block** stage as visual hero (~2/3) — interactive
- Short support: title / day N/M when multi-day
- Sticky footer by Guide shape (`horizon_days`):
  - **Same-day** (`horizon_days === 1`): **Back** + **Next**; last step of the day → **Back** + **Done**
  - **Daily** (`horizon_days > 1`): one **Done**
- Header: back **‹** only (no “Continue” title); right **kebab** (not burger)
- Kebab: Full Guide · Edit Session (stub) · Postpone to tomorrow (daily only) · Skip · Finish cycle (if allowed) · Archive
- AI Repair / lighten / rest — **not** on Session happy path (`RepairSheet` kept for future Edit Session)

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
