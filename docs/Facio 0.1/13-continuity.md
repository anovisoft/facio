# 13 — Continuity (do not lose after chat summary)

Working memory across sessions. Product canon = `01`–`11`. Process = [12](./12-process.md). Slices = [14](./14-impl-plan.md). Polish triage: `docs/polishing bugs.txt`.

**Update this file** when a slice is accepted, a landmine is found, or PO decides an open question.

---

## Snapshot (2026-08-05)

| Layer | State |
|-------|--------|
| Product vector | Facio 0.1 locked — **Guide / Continue / Session** + Hero/Full/Compact + **Plan Feed · Manual · Micro** ([15](./15-edit-surfaces.md)) |
| Prototype engine | `apps/` ≈ `docs/next` slices 1–5 **accepted** |
| Facio 0.1 shell | **A–E2b + E2a-iterate accepted**. **E2b-iterate landed** (await PO dogfood #11–13) → then **E2c** → F → G |
| Edit surfaces lock | Create = Plan Feed + Manual (CTA on plan card, no sticky Start). Active = Manual + Micro + AI Feed. Canon [15](./15-edit-surfaces.md) |
| Carbonara / multi-Session same day | Same-day **Back/Next = browse**; **Done** completes live step (assurance); last Done → Continue |
| Fitness multi-day E2E | Daily sticky **Done** + assurance; kebab Postpone (deterministic); deferred calendar week / **H** |
| Instant Answer | Off Create happy path (D5) |
| Uncommitted work | Large client+backend under `apps/` (E→E2b, chrome, planFeed, manualEdit, Alembic `013`) — **not committed** |

---

## After summarization — PM start here

1. Read [README](./README.md) → [15](./15-edit-surfaces.md) → [11](./11-success-systems.md) (§5–6 Diff/Undo, §9) → **this file** → [14](./14-impl-plan.md).  
2. **E2b-iterate landed** (await PO dogfood #11–13). On accept → **E2c**.  




3. Do **not** invent D1–D8 / deferred parked items.  
4. Do **not** reopen Guides reveal (`useGuidesRevealGesture`, `useNativeDriver: false`) unless PO reports regress.  
5. Do **not** expand Anthropic schemas beyond E2a-iterate’s tiny clarify `selection` enum. Repair landmines (lighten/rest strip plugins) still apply — E APIs backbone of E2c.  

6. Plan Feed history is **client MMKV** only — server-side turns = known follow-up (not blocking E2c unless PO prioritizes).

---

## Fragile knowledge (summary will drop this — keep here)

### Roles & process

- **PO** = human; **PM** = lead agent this chat; **Devs** = Task subagents (`cursor-grok-4.5-high` for impl; Composer only for cheap mechanical).
- One slice (or one locked polish pass) per subagent run. Spec = `docs/Facio 0.1/`.
- After each accepted slice → update this status table.

### Doc pack roles

| Path | Role |
|------|------|
| `docs/Facio 0.1/` | **Source of truth** UX/IA/terms/success systems |
| `docs/next/` | Runtime engine (cycles, plugins, physical day, grammar) |
| `docs/mvp/` | Frozen first experiment |
| `docs/RFC/` | Long-horizon — do not override 0.1 UX |

Conflict → **Facio 0.1 wins** on surface; keep next engine.

### Product stack (locked)

```text
Guide     → path (strategy)     — Compact Summaries + Cover
Continue  → focus (tactics)     — Hero Preview attention stack
Session   → execution           — Full Block interactive
Drawer    → inventory nav       — compact list (not twin Continue)
```

Presentations: **Hero Preview** / **Full Block** / **Compact Summary** — [11 §9](./11-success-systems.md).  
Hero Preview **read-only**. Idle Guides (no `next_action`) → drawer only.

One-liner: **Guide determines the path. Continue determines the focus. Session ensures execution.**

### Anthropic structured output landmine

- `400 grammar too large` — do not merge plugins into `#2` Path schema  
- Create **3-phase**: `#1` gate → `#2` Path + `plugin_hints` → `#3` materialize after Start  
- Failed `#2`/`#3` must persist errors (`path_error` / `plugins_error`)  
- Detail: `docs/next/09-continuity.md`

### Physical day / Session atom

- Execute only `day_index ≤ unlocked_day_index`  
- D2: incomplete Block runtime resume = **same calendar day only** (`blockRuntimeByActionId` + `localDate`)  
- Complete routing: same-day **Done** on a non-last live step → stay on next Session (toast); **Done** (daily / last same-day) → Continue after assurance. Same-day Back/Next never complete.

### Session chrome lock (PO 2026-08-04 / browse fix 2026-08-05) — implemented / awaiting dogfood

| Mode | When | Sticky footer |
|------|------|----------------|
| Same-day plan | `horizon_days <= 1` | **Back** + **Next** browse peers; live step also **Done** (last pending → **Back** + **Done**; not last → **Done** full-width + **Back**\|**Next**) |
| Daily Guide | `horizon_days > 1` | one **Done** |

- Same-day **Back** / **Next** = browse only among same-day Sessions (no `complete`, no `uncomplete`, no checkbox auto-mark). Peeking → Full Block read-only + browse hint.
- **Done** = complete the live `next_action` only (assurance: “Finish session?” → Cancel / Done; checklist note if unchecked items remain). Counter never incomplete-gates. After complete, browse clears to the new live next.
- Header: `GlassIconButton variant="header"` (icon only) in `headerLeft`/`headerRight` — iOS 26 draws **one** system glass; bordered/`nav` chips double it. Kebab menu = native `Alert.alert` (compact UIAlertController). Do **not** use `unstable_header*Items` `button`/`menu` on screens@4.16 (unsupported → buttons vanish). Continue ☰ stays `default` LiquidGlass in-content.
- Kebab options: Full Guide · Edit Session (stub) · Postpone to tomorrow (daily only, `POST /projects/{id}/postpone-day`, no LLM) · Skip · Finish cycle · Archive (destructive).
- Repair / lighten / rest off Session happy path; keep `RepairSheet.tsx` for future Edit Session.

### Guides drawer reveal landmines

- Not RN Modal bottom-sheet. Guides **under** Continue; translateX ~82%; radius ~52; **no scale**.  
- `useGuidesRevealGesture.ts`: `useNativeDriver: false`; don’t drive mid-drag off stale `drawerOpen`.  
- Stay Expo RN.
- **Session → Continue terminal exit:** Done / Skip (no next) / Postpone / Archive must `resetToContinue` (`reliableBack.tsx`), not `navigate('Continue')`. Otherwise Session stays under Continue and iOS edge-swipe returns to Session instead of opening Guides.

### Device / API

- Physical device: `apps/mobapp-rn/.env` → `EXPO_PUBLIC_API_URL` = Mac LAN IP (changes → infinite Continue load).  
- Docker: postgres `:5435`, backend `:8000`. Auth: `X-Device-Id`.

### Mapping prototype → 0.1 (aliases first — D6)

| Code | Product |
|------|---------|
| Project / ProjectHome | Guide / Session |
| Path / DraftStudio | → unified `GuideScreen` |
| plugins | UI Blocks |
| `state_versions` | Undo foundation (E) |

---

## Open PO decisions (do not invent)

| ID | Default until PO speaks |
|----|-------------------------|
| D1 | Focus: overdue > last day (horizon>1) > short ≤5m > others; no pin |
| D2 | Same-calendar-day resume only |
| D3 | Streak = consecutive days with ≥1 Session complete on Guide |
| D4 | Commitment = sticky CTA on Guide (no separate route) |
| D5 | Instant Answer off happy path |
| D6 | Aliases first; rename project→guide later |
| D7 | Cover: heuristic on Path apply OK; LLM fill when safe |
| D8 | Next Cycle = chapter; Finish = Guide success met |

**Also locked (not open):** Hero read-only; drawer compact; Hero/Full/Compact naming; Session→Guide = ≡ only (no full-screen swipe-up); complete routing next-Session vs Continue; checklist Done confirm (mark remaining); Continue card grid (title → Hero → footer ≈min \| grit).

---

## Deferred / parked (do not invent)

| Item | Reopen |
|------|--------|
| Auto AI after measure (#3) | After E / explicit PO |
| Guides search; Archive → status tags (#5) | Later / F for Repeat |
| Domain-neutral rest/day copy (#8) | **Slice G** — `path.restEmpty`, `dayKind.*`, LLM titles |
| Offline / no-network (P5) | Needs cache design — Continue+Session from cache |
| Bottom-edge Session→Guide swipe strip | Only if PO reopens |

---

## Slice status

| Slice | Name | Status |
|-------|------|--------|
| A | IA shell | **accepted** |
| B | Focus Engine v0 + Cover | **accepted** |
| B2 | Hero Preview + drawer compact | **accepted** |
| C | Guide Explore + Commitment | **accepted** (after Explore UX iterate) |
| D | Session atom + complete + ≡ Guide | **accepted** (after complete-routing + chrome + P1–P4 polish) |
| E | Repair Diff + Undo | **accepted** (PO 2026-08-05) |
| — | Session chrome cleanup | **accepted** (PO 2026-08-05) |
| E2a | Create Plan Feed | **accepted** (PO 2026-08-05) |
| E2b | Manual editor (all tools) | **accepted** (PO 2026-08-05; checklist drag UI polish included) |
| E2a-iterate | Create questions-first + bg path + selection (#9) | **accepted** (PO 2026-08-05) |
| E2b-iterate | Manual entry + checklist polish (#11–13) | **landed** (await PO dogfood) |
| E2c | Active AI Feed + Diff (#10) | **next** after E2b-iterate accept |
| F | Identity + Finish Experience | pending (after E2*) |
| G | Copy / IA kill / Morning Summary (+ #8) | pending |
| H | Time travel (optional) | pending |

---

## What landed — quick index (client)

| Area | Where |
|------|--------|
| Continue + Focus | `features/continue/` — `focusEngine.ts`, `heroPreview/`, card grid in `ContinueScreen` |
| Guides reveal | `useGuidesRevealGesture.ts` + `GuidesDrawer.tsx` |
| Cover | Alembic `012`, `cover.py`, `coverDisplay.ts` |
| Guide trust | `features/guide/GuideScreen.tsx` (+ CompactRoadmap, Cover, contract, softStart) |
| Session | `features/home/ProjectHomeScreen.tsx` — sticky footer by horizon, kebab, Back/Next/Done, checklist/Done assurance |
| Session APIs | `POST /actions/{id}/uncomplete`; `POST /projects/{id}/postpone-day` (Alembic `013` `user_edit`) |
| Stepper persist/back | `ActionPlugins.tsx` + store `blockRuntimeByActionId` |
| Glass chips | `GlassIconButton` — `GLASS_ICON_CHIP_SIZE`; Session header = `header` icons + native Alert kebab; Continue ☰ = `default` |
| Scroll | `SafeScreen` — scroll outside KAV; `flexGrow: 0`; PathList expandable on Guide |
| Repair Diff + Undo (E) | `RepairSheet` Diff confirm; preview/apply; active Undo; lighten/rest strip plugins + phase-3 rematerialize (shift preserves) |
| Plan Feed (E2a) | `features/guide/planFeed/*` — append-only лента; MMKV `planFeedByProjectId` |
| Manual editor (E2b) | `features/manualEdit/*` — Create «Edit tools» + Active Edit Session; `GET path-state` / `POST manual-edit` |

---

## Engineering pointers

- Client: `apps/mobapp-rn`  
- API: `apps/backend-py3/client-service` — Alembic through **013**  
- Prefer aliases over big-bang DB rename  
- Subagent model slug in this env: `cursor-grok-4.5-high-fast` (not `cursor-grok-4.5-high`)

Do not rewrite backend runtime — next lettered slice = **E2c Active AI Feed** ([15](./15-edit-surfaces.md)), then F.

### Edit surfaces lock (PO 2026-08-05)

- Create = Plan Feed + Manual; Start CTA **on each plan card**; no sticky bottom Start.
- Active = Manual + Micro (skip/postpone chrome) + AI Feed; AI apply → Diff → Undo.
- Manual must edit **all** UI Block tools (checklist/stepper/…).
- New AI plan = append card; may ask questions without new plan.
- Clarify = optional chips + free-form **in same feed block**; chip answers not required.
- Canon: [15](./15-edit-surfaces.md).

### Session chrome lock (browse fix) — accepted

- Same-day **Back/Next = browse only** (no complete, no uncomplete, no auto-check). Peek → read-only Block + hint.
- **Done** = complete live `next_action` only (assurance). Daily Guide = single Done.
- Header: `GlassIconButton variant="header"`; kebab = native `Alert.alert`. Do **not** use `unstable_header*Items` on screens@4.16.
- Terminal exits (Done/Skip/Postpone/Archive) → `resetToContinue`, not `navigate('Continue')`.

### E2a Plan Feed — accepted

Append-only лента; questions during soft-start; refine waits for path; Start on card; feed history **client MMKV** (server turns = follow-up). Code: `features/guide/planFeed/*`.

### E2b Manual editor — accepted (PO 2026-08-05)

Shared Manual for closed Block tools. Create: plan card «Edit tools». Active: Session kebab → Manual + Undo. API: `GET .../path-state`, `POST .../manual-edit` (`user_edit`). Checklist UI: drag handle left, red X delete, slot-shift preview while dragging (`ManualBlockEditor.tsx`). Code: `features/manualEdit/*`. Tests: `tests/test_manual_edit.py`.

### External dogfood triage (PO paste 2026-08-05)

| # | Finding | Bucket | Slice |
|---|---------|--------|-------|
| 9 | Create: didn’t expand plan; answered Qs but never «Update path» | Create polish | **E2a-iterate** — questions-first + bg `#2` + skip/answer branches + `selection` |
| 10 | Manual removed ingredient; expected whole-plan cascade; no path back to plan dialog | Product gap = E2c | **E2c** — pencil/back → Edit/AI Feed; Manual **«Save with AI»** seeds rebuild; Diff + accept with progress preserve |

**PM read:** #10 is exactly why Active AI Feed exists — Manual alone patches tools, not the narrative path. #9 is Create UX, not E2c.

### E2a-iterate lock (PO 2026-08-05) — replacing prior expand-only pass

```text
Intent → gate (#1) → questions FIRST (sense OK)
         └─ background #2 Path (hidden until user acts)

A) Answer / free-form → wait #2 → refine → show plan (no Intent-plan flash)
B) Skip «without answers» → reveal Intent-only plan when ready
                           → same questions under that plan
```

- Per-question `selection`: `single` | `multi` from AI (default single).
- Plan expanded when shown. No change to LLM “session” (still `current_state` per call).
- Compact history into refine prompts = **parked** (PO).

### E2a-iterate — accepted (PO 2026-08-05)

Questions-first Create; `planRevealMode`; skip→Intent plan+Qs; answers→refine (no flash); `selection` single|multi. LLM session unchanged.

### E2b-iterate — landed (await PO dogfood; #13 rewrite)

#11 clarify TextInput; #12 Block Edit+pencil; #13 checklist drag **rewritten** (absolute overlay + margin gap — prior native/JS transform mix left dragged row stuck / floating). Re-dogfood drag 4→1.

### Pending

1. PO dogfood E2b-iterate → accept → **E2c** (#10).  
2. Parked: server feed turns; compact refine history; #8 → G; offline P5.
