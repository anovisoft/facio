# 13 — Continuity (do not lose after chat summary)

Working memory across sessions. Product canon = `01`–`11`. Process = [12](./12-process.md). Slices = [14](./14-impl-plan.md). Polish triage: `docs/polishing bugs.txt`.

**Update this file** when a slice is accepted, a landmine is found, or PO decides an open question.

---

## Snapshot (2026-08-03 evening)

| Layer | State |
|-------|--------|
| Product vector | Facio 0.1 locked — **Guide = path / Continue = focus / Session = execute** + Hero/Full/Compact |
| Prototype engine | `apps/` ≈ `docs/next` slices 1–5 **accepted** |
| Facio 0.1 shell | **A–D accepted** (incl. C/D iterates + chrome + evening polish P1–P4). **E implemented / awaiting PO dogfood**. **Next after accept = Slice F** |
| Carbonara / multi-Session same day | Complete routing: next Session in-place (no modal→Continue) |
| Fitness multi-day E2E | Deferred — calendar week or **Slice H** time travel |
| Instant Answer | Off Create happy path (D5) |
| Uncommitted work | Large client+backend under `apps/mobapp-rn/` + cover Alembic `012` — **not committed** (incl. Slice E Repair Diff+Undo) |

---

## After summarization — PM start here

1. Read [README](./README.md) → [11](./11-success-systems.md) (esp. §5–6 Diff/Undo, §9 presentations) → **this file** → [14](./14-impl-plan.md).  
2. Confirm with PO: **dogfood Slice E?** then accept → dispatch **Slice F** (Identity + Finish).  
3. Slice E landed (awaiting PO dogfood — not accepted yet):
   - Repair: intent → **preview Diff** → confirm → apply (no silent apply).
   - API: `POST .../repair/preview` + apply with `proposed_state` / `before_version`; response `undo_version`.
   - Undo: `restore-state` works on **active** (materialize merge) as well as draft.
   - Session banner: summary + **Undo** CTA after apply.
   - **Landmine fixed:** lighten/rest strip plugin payloads + rematerialize phase-3 (shift still preserves). Do **not** re-introduce blind `_preserve_plugins` on all repairs.
   - Do **not** expand Anthropic schemas.
4. Do **not** invent D1–D8 / deferred parked items.  
5. Do **not** reopen Continuereveal (`useGuidesRevealGesture`, `useNativeDriver: false`) unless PO reports regress.  
6. After E accept → **F** (Identity + Finish).

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
- Complete routing: if same Guide still has `next_action` → **stay on next Session** (light toast); else → Continue. **No** Session-complete modal / progress bar on Done.

### Guides drawer reveal landmines

- Not RN Modal bottom-sheet. Guides **under** Continue; translateX ~82%; radius ~52; **no scale**.  
- `useGuidesRevealGesture.ts`: `useNativeDriver: false`; don’t drive mid-drag off stale `drawerOpen`.  
- Stay Expo RN.

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
| E | Repair Diff + Undo | **implemented / awaiting PO dogfood** |
| F | Identity + Finish Experience | **next** (after E accept) |
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
| Session | `features/home/ProjectHomeScreen.tsx` — layout, complete routing, checklist confirm, optimistic toggles |
| Stepper persist/back | `ActionPlugins.tsx` + store `blockRuntimeByActionId` |
| Glass chips | `GlassIconButton` — `GLASS_ICON_CHIP_SIZE`; Session ≡ `variant="header"` |
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
- API: `apps/backend-py3/client-service` — Alembic through **012**  
- Prefer aliases over big-bang DB rename  

Do not rewrite backend runtime to start Facio 0.1 — shell + trust mutations next (E).
