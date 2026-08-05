# 13 — Continuity (do not lose after chat summary)

Working memory across sessions. Product canon = `01`–`11`. Process = [12](./12-process.md). Slices = [14](./14-impl-plan.md). Polish triage: `docs/polishing bugs.txt`.

**Update this file** when a slice is accepted, a landmine is found, or PO decides an open question.

---

## Snapshot (2026-08-05)

| Layer | State |
|-------|--------|
| Product vector | Facio 0.1 locked — **Guide / Continue / Session** + Hero/Full/Compact + **Plan Feed · Manual · Micro** ([15](./15-edit-surfaces.md)) |
| Prototype engine | `apps/` ≈ `docs/next` slices 1–5 **accepted** |
| Facio 0.1 shell | **A–E2a accepted**. **E2b Manual editor landed** (awaiting PO dogfood) → E2c Active AI Feed → F |
| Edit surfaces lock | Create = Plan Feed + Manual (CTA on plan card, no sticky Start). Active = Manual + Micro + AI Feed. Canon [15](./15-edit-surfaces.md) |
| Carbonara / multi-Session same day | Same-day **Back/Next = browse**; **Done** completes live step (assurance); last Done → Continue |
| Fitness multi-day E2E | Daily sticky **Done** + assurance; kebab Postpone (deterministic); deferred calendar week / **H** |
| Instant Answer | Off Create happy path (D5) |
| Uncommitted work | Client+backend under `apps/` — Session chrome + E Repair + Alembic `013` — **not committed** |

---

## After summarization — PM start here

1. Read [README](./README.md) → [11](./11-success-systems.md) (esp. §5–6 Diff/Undo, §9 presentations) → **this file** → [14](./14-impl-plan.md).  
2. **E2a accepted** (PO 2026-08-05). **E2b Manual** implemented — dogfood then accept → **E2c**.  
3. Slice E accepted — keep landmines:
   - Repair: intent → **preview Diff** → confirm → apply (no silent apply).
   - API: `POST .../repair/preview` + apply with `proposed_state` / `before_version`; response `undo_version`.
   - Undo: `restore-state` works on **active** (materialize merge) as well as draft.
   - **Landmine:** lighten/rest strip plugin payloads + rematerialize phase-3 (shift still preserves). Do **not** re-introduce blind `_preserve_plugins` on all repairs.
   - Do **not** expand Anthropic schemas. E APIs become backbone of Active AI Feed (E2c).
4. Session chrome accepted — see lock below. Repair off Session happy path → Edit surfaces ([15](./15-edit-surfaces.md)).
5. **Edit surfaces locked** ([15](./15-edit-surfaces.md)): Plan Feed + Manual + Micro. Next code after E2b dogfood: **E2c** → F.
6. Do **not** invent D1–D8 / deferred parked items.  
7. Do **not** reopen Guides reveal (`useGuidesRevealGesture`, `useNativeDriver: false`) unless PO reports regress.

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
| E2b | Manual editor (all tools) | **landed** (awaiting PO dogfood) |
| E2c | Active AI Feed + Diff | pending |
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

---

## Slice E — landed (awaiting PO dogfood)

Implemented 2026-08-03; lighten rematerialize fix 2026-08-04:

1. **Diff before apply:** intent → `POST /repair/preview` (no persist) → Diff sheet → Confirm → `POST /repair` with `proposed_state` + `before_version`.  
2. **Undo on active:** `restore-state` rematerializes with `merge_progress` for active Guides; apply returns `undo_version`.  
3. **Session CTA:** post-apply banner shows summary + **Undo** (not debug-only).  
4. **Plugin landmine (fixed):** Repair wire is hints-only (like create #2). `_preserve_plugins` used to copy old stepper/counter onto matching ids — so lighten Diff could change titles while Session kept the old push-up load. Now `_prepare_repair_state`: **shift** preserves plugins; **lighten/rest** strip payloads + keep hints → `plugins_ready=false` → phase-3 enqueue on apply (same as commit). Diff adds `Previous load (sets) → Lighter load (tool updates)` when tools were stripped.  
5. Still out of scope: AI Edit UI, new repair intents, #8 copy, grammar expand.

**PO dogfood E:** Repair → see Diff (incl. load line on lighten) → apply → stepper updates → Undo works → then accept.

---

## Engineering pointers

- Client: `apps/mobapp-rn`  
- API: `apps/backend-py3/client-service` — Alembic through **013**  
- Prefer aliases over big-bang DB rename  

Do not rewrite backend runtime to start Facio 0.1 — next after E2b dogfood = **E2c Active AI Feed** ([15](./15-edit-surfaces.md)), then F.

### Edit surfaces lock (PO 2026-08-05)

- Create = Plan Feed + Manual; Start CTA **on each plan card**; no sticky bottom Start.
- Active = Manual + Micro (skip/postpone chrome) + AI Feed; AI apply → Diff → Undo.
- Manual must edit **all** UI Block tools (checklist/stepper/…).
- New AI plan = append card; may ask questions without new plan.
- Canon doc: [15](./15-edit-surfaces.md).

### E2a Plan Feed (client) — accepted (PO 2026-08-05)

Draft Guide Explore is an append-only лента — user intent, sense, versioned plan cards (Cover + contract + CompactRoadmap + Start on card), clarify block (optional chips + free-form **in the same card**); no sticky Start / no separate notes footer. Chip answers not required — note alone can refine. **Questions show during soft-start** before Path v1 ready (refine waits for path). Prior cards remain after refine; Start on an older card restores that `state_version` then commits. Feed history persisted client-side per project (MMKV); server-side turns = follow-up. Progressive create unchanged. Code: `features/guide/planFeed/*`.

### E2b Manual editor — landed (awaiting PO dogfood)

Shared Manual editor for closed UI Block tool fields (checklist add/remove/edit; stepper targets/labels/rest duration; counter target/label; timer/timeline/interval scalars when present; hints-only graceful note). **Create:** plan card «Edit tools» loads that card’s `state_version` read-only (`GET .../path-state?version=`), Save restores tip if needed then `POST .../manual-edit` (`user_edit` + `proposed_state` / `before_version`, `undo_version`); feed card updates in place. **Active:** Session kebab Edit Session → Manual scoped to live/browse action key; apply → Undo banner via `restore-state`. No AI Feed (E2c). Code: `features/manualEdit/*`, backend `manual_edit` / `path-state`. Tests: `tests/test_manual_edit.py`.
