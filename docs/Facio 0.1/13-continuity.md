# 13 — Continuity (do not lose after chat summary)

Working memory across sessions. Product canon = `01`–`11`. Process = [12](./12-process.md). Slices = [14](./14-impl-plan.md).

**Update this file** when a slice is accepted, a landmine is found, or PO decides an open question.

---

## Snapshot (2026-08-03)

| Layer | State |
|-------|--------|
| Product vector | Facio 0.1 locked — **Guide = path / Continue = focus / Session = execute** + Hero/Full/Compact presentations |
| Prototype engine | `apps/` ≈ `docs/next` slices 1–5 **accepted** |
| Carbonara dogfood | OK (timeline → finish → Repeat) |
| Fitness multi-day E2E | Deferred — needs calendar week or **dev time travel** |
| Facio 0.1 code shell | **A–D accepted**. **D-chrome iterate landed** — await PO dogfood. E paused |
| Instant Answer | Off Create happy path (D5); screen may remain registered dead |

---

## Fragile knowledge (summary will drop this — keep here)

### Roles & process

- **PO** = human; **PM** = lead agent this chat; **Devs** = Task subagents (`cursor-grok-4.5-high` for impl; Composer only for cheap mechanical).
- One slice per subagent run. Spec = `docs/Facio 0.1/`. Do **not** invent D1–D8.
- After each accepted slice → update this status table.

### Doc pack roles

| Path | Role |
|------|------|
| `docs/Facio 0.1/` | **Source of truth** for UX/IA/terms/success systems |
| `docs/next/` | How runtime was built; grammar splits; physical day; stepper |
| `docs/mvp/` | Frozen first experiment |
| `docs/RFC/` | Long-horizon Outcome OS — do not override 0.1 UX |

Conflict → **Facio 0.1 wins** on surface; keep next engine.

### Product stack (PO locked 2026-08-03)

```text
Guide     → path (strategy)     — page with Compact Summaries
Continue  → focus (tactics)     — Hero Preview attention stack
Session   → execution           — Full Block interactive
Drawer    → inventory nav       — compact list (not twin Continue)
```

Presentations (prefer names over S/M/L): **Hero Preview** / **Full Block** / **Compact Summary** — see [11 §9](./11-success-systems.md).  
Hero Preview is **read-only** in 0.1. Idle Guides (nothing today) → drawer only, not Continue.

### Anthropic structured output landmine

- Error: `400 grammar too large` on constrained JSON schema  
- **Sonnet does not fix it** — same grammar limit as Haiku  
- Create is **3-phase**: `#1` gate/start → `#2` Path + `plugin_hints` (no plugin objects) → `#3` materialize plugins after Start  
- Do not merge full PathState + InstantAnswer + plugins into one schema  
- Failed `#2`/`#3` must still commit audit (`llm_calls` / error turns)  
- Detail: `docs/next/09-continuity.md` (Anthropic section)

### Physical day

- Execute only `day_index ≤ unlocked_day_index`  
- Future days preview OK, controls disabled  
- Closing day N early must **not** unlock N+1 same calendar day  
- Repair must respect unlock  

### Session Stage (already in code spirit)

- Block hero ~2/3; burger → full plan  
- Wire plugin name **`stepper`** (not `set_plan`); beats `measure|work|rest`  
- Strength: one session action / day; no checklist-as-sets  

### Mapping prototype → 0.1 (code names still old)

| Code today | Product 0.1 |
|------------|-------------|
| `Project` | Guide |
| `ProjectsScreen` | → Continue + drawer (re-export / alias) |
| `ProjectHomeScreen` | → Session |
| `PathScreen` / `DraftStudioScreen` | → **Guide** (unified trust; GuideExplore alias) |
| `InstantAnswerScreen` | → cut from happy path |
| `HistoryScreen` | → Archive |
| plugins | UI Blocks |
| `state_versions` | Undo foundation |

Prefer **aliases / new screens** over big-bang DB rename (D6).

### Slice A — what landed (client)

| Piece | Where |
|-------|--------|
| Root = Continue | `navigation/index.tsx` `initialRouteName="Continue"` |
| Routes | Continue, Create, Session, Guide, GuideExplore, Archive, Settings (+ dead InstantAnswer) |
| Continue home | `features/continue/ContinueScreen.tsx` |
| Guides under-sheet | ChatGPT reveal: Guides behind Continue; main translates ~82%; radius ~52; **no scale** |
| Reveal gesture | `useGuidesRevealGesture.ts` — **PO OK**; `useNativeDriver: false`; do not regress lightly |
| Guides list + gear | `features/continue/GuidesDrawer.tsx` — Archive + glass Settings gear |
| Glass chips | `shared/ui/GlassIconButton.tsx` + Ionicons |
| Settings (theme) | `features/settings/SettingsScreen.tsx` |
| Create | Instant Answer off happy path → GuideExplore |

### Slice B — what landed (accepted)

| Piece | Where |
|-------|--------|
| Focus Engine v0 | `features/continue/focusEngine.ts` — D1 tiers; `README.md` |
| Cover columns | `projects.cover_emoji` / `cover_difficulty` / `cover_duration_summary` (Alembic `012`) |
| Cover fill | Heuristic on `apply_contract` (`app/services/cover.py`) — no Anthropic grammar expansion |
| Cover UI | B2: Continue = Hero Preview; drawer = compact mark+title (Cover meta not card body) |

### Slice B2 — what landed (code done, await PO dogfood)

| Piece | Where |
|-------|--------|
| Hero Preview | `features/continue/heroPreview/` — checklist / stepper / timeline / timer + fallback |
| Attention filter | `focusEngine.ts` `needsAttention` — waiting Guides off Continue |
| Continue cards | `ContinueScreen.tsx` — Session Hero + Focus chip; Guide emoji = small mark |
| Drawer compact | `GuidesDrawer.tsx` — mark + title + thin draft/waiting; no Cover twin cards |
| Contract doc | `features/continue/README.md` |

### Device / API landmine

- Physical device needs Mac LAN IP in `apps/mobapp-rn/.env` → `EXPO_PUBLIC_API_URL`  
- IP changes on network switch → infinite Continue loading while backend healthy on localhost  
- Backend docker: `:8000`; postgres `:5435`

### Guides drawer UX landmines (learned this wave)

- **Not** RN `Modal` + `animationType="slide"` (feels like bottom sheet).  
- Guides = sheet **under** Continue; Continue slides right (~82%).  
- Do not drive finger math off stale `drawerOpen` boolean.  
- Avoid scale-on-open. Radius ~52.  
- Working gesture: `translateX` px + spring; **`useNativeDriver: false`**.  
- If broken → fix `useGuidesRevealGesture.ts`, don’t stack patches in ContinueScreen.  
- Stay on **Expo RN**.  
- **PO (2026-08-03):** drawer = **compact nav list** (B2 code) — mark + title + thin status; not Cover twin of Continue.

### Success systems that must not be “later polish”

From [11](./11-success-systems.md): Focus Engine, Session presentations (Hero/Full/Compact), Session complete beat, Session atom, finite Guide, Repair Diff, Undo, Cover, Identity, Finish Experience.

---

## Open PO decisions (block silent invention)

| ID | Question | Default until PO speaks |
|----|----------|-------------------------|
| D1 | Focus Engine weights / pin Focus? | Deterministic v0: overdue > last day > short ≤5m > others; no pin |
| D2 | Incomplete Session resume window? | Same calendar day only; else incomplete → reschedule/repair path |
| D3 | Streak definition? | Consecutive calendar days with ≥1 Session complete on Guide |
| D4 | Commitment separate route? | Sticky CTA on Guide (no separate route) |
| D5 | Instant Answer? | Remove from happy path (hide or delete) |
| D6 | `project`→`guide` rename when? | After shell works; aliases first |
| D7 | Cover generation? | LLM fills emoji+difficulty+duration_summary on create #1/#2 (v0 = heuristic fallback OK) |
| D8 | Finish vs Next Cycle confusion in UI? | Next Cycle = chapter; Finish = Guide success criteria met |

**Locked (not open):** Hero Preview read-only in 0.1; drawer compact vs Continue Hero; naming Hero/Full/Compact (not S/M/L).

### Deferred / parked (PO 2026-08-03 — do not invent)

| Item | Note | Reopen when |
|------|------|-------------|
| Auto AI after measure | Background plan modernize post-stepper measure | After E / explicit PO scope — not shell |
| Guides search | Drawer search | Later polish |
| Archive → status tags | Maybe replace Archive with status tags for repeat-cook cases | PO decision; Repeat path = Slice F |
| Full UI chrome audit | Unify all controls beyond menu chips | After D Session recompose |
| Domain-neutral rest / day kinds | Rest/train copy leaks fitness into non-sport Guides (e.g. drawing rest shows «без силовой нагрузки»; day kind «Тренировка»). Root: client `path.restEmpty` / `dayKind.*` + LLM day titles. Fix domain-aware copy or LLM prompts — **not Slice D**. | **Slice G** (copy) or create `#2` prompt pass |

Tracked also in `docs/polishing bugs.txt` (#8).

### Hotfix after B2 (**done**)

| # | Fix |
|---|-----|
| 1 | Unify glass menu size (`GLASS_ICON_CHIP_SIZE = 40`); Session header → GlassIconButton + Ionicons |
| 4 | `lastDay` chip only if `horizon_days > 1` AND unlock is last day |

---

## Slice status

| Slice | Name | Status |
|-------|------|--------|
| A | IA shell (nav: Continue / Session / Guide / Create / drawer) | **accepted** (PO 2026-08-03) |
| B | Focus Engine v0 + Cover on cards | **accepted** (PO 2026-08-03) |
| B2 | Hero Preview + drawer compact | **accepted** (PO 2026-08-03) |
| C | Guide Explore trust (roadmap + Commitment; fold Draft) | **accepted** (PO 2026-08-03, after iterate) |
| D | Session atom + Session complete beat + ≡ → Guide | **accepted** — **chrome iterate landed** (await PO dogfood) |
| E | Repair Diff + Undo | **paused** (PO) until Session↔Guide chrome settled |
| F | Identity + Finish Experience | pending |
| G | Copy/i18n + kill Instant Answer + Morning Summary | pending |
| H | (optional) time travel for fitness dogfood | pending |

---

## Engineering pointers (apps)

- Client: `apps/mobapp-rn` — Expo RN, nav in `src/navigation/`  
- API: `apps/backend-py3/client-service` — FastAPI, Alembic through `012`  
- Auth: `X-Device-Id`  
- Docker: postgres `:5435`, backend `:8000`  

Do not start Facio 0.1 by rewriting the backend runtime. Shell first. Uncommitted A/B work under `apps/mobapp-rn/` + backend cover migration.

---

## After summarization — PM start here

1. Read [README](./README.md) → [11](./11-success-systems.md) (§9) → **this file** → [14](./14-impl-plan.md)  
2. A–D **accepted**. **E paused**. Next: PO dogfood D-chrome iterate (below), then E.  
3. Do **not** invent deferred #3 / #5; #8 → G.  
4. Do **not** reopen Continuereveal gesture unless PO reports regress.

### Session ↔ Guide chrome — PO locked (2026-08-03) → **iterate landed**

1. **Removed** Session full-screen swipe-up → Guide (and «Swipe up — Guide» hint). **≡ only** (`fromSession: true` on navigate).
2. **Scroll bound** — dropped `PanGestureHandler` wrap; `SafeScreen` scroll uses `flexGrow: 0` (no empty rubber-band void). Guide same pattern.
3. Guide sticky CTA: `fromSession` → secondary **Back to Session** (`goBack`); else **Start Session** when `next_action`.
4. From Session: `detailExpanded` / PathList **true by default**; Compact roadmap still on top.

**E remains paused** until this iterate dogfood OK.

### Slice D — what landed (client, 2026-08-03)

| Piece | Where |
|-------|--------|
| Session complete routing (D iterate) | `ProjectHomeScreen.onComplete` — after refresh: `next_action` → stay + light flash; else → Continue. **No modal. No progress bar.** |
| Light Done flash | Inline banner `sessionDoneToast` / `sessionNextToast` (EN+RU); auto-dismiss ~1.8s |
| FirstCompletionOverlay | **deleted** — no first-mode modal on Session Done |
| firstCompletion store flags | **removed** from `store/index.ts` |
| D2 same-day runtime | `store` `blockRuntimeByActionId` keyed by `actionId` + `localDate`; expire/clear when date ≠ today |
| Stepper back + persist | `StepperPlayer` — Back/Next; hydrate beatIndex/rest; clear rest on step back; clear on Done/Skip |
| Session layout #7 | `ProjectHomeScreen` — title → Day N/M (multi-day only) → large Full Block → detail / Why demoted |
| ≡ → Guide (chrome iterate) | `GlassIconButton variant="header"` → `navigate('Guide', { fromSession: true })`. Swipe-up **removed** (`useSessionGuideSwipe` deleted) |
| Guide from Session | sticky **Back to Session**; full plan expanded by default |
| Scroll bound | `SafeScreen` — no pan wrap; `contentContainerStyle.flexGrow: 0` |
| Counters | Still server-backed; runtime store is position/clocks only |

**D2 behavior:** incomplete Session resume is **same calendar day only**. Cross-day open starts fresh beat index (server counters may remain). No multi-day mid-beat happy path.

**Complete routing (PO locked, landed):** After Done + refresh — if Guide still has executable `next_action` → next Session in-place (light toast); else → Continue. Progress bar / first-completion modal gone from Done chrome. Guide-level progress → Finish (F).

**Status:** **D-chrome iterate landed** (2026-08-03) — await PO dogfood (carbonara shopping→cooking). On accept → E.

### Slice C iterate — PO dogfood (2026-08-03)

**Reject reasons:** Explore feels like a nuclear control panel; softStart prefix doubles; Session ≡ double outline; path ready invisible while clarifying; footer has Back+Refine+Start+Save.

**Locked UX for iterate (PM, PO-aligned):**

1. **softStart once** — if `paraphrase` already contains the soft-start prefix, do not wrap again; do not show softStart line + Cover title that repeat the same string.
2. **Day labels** — avoid `День N · День · title` (skip redundant kind when kind is generic "day").
3. **Footer draft:** sticky **only Start Guide**. Back/undo version = header or text under clarify. Refine = next to clarify answers (not footer). Save-only = tertiary text link or omit (Start Guide is the commit).
4. **Order:** Cover → path status/roadmap (skeleton while loading) → clarify below. When `path_ready` flips true, show clear **«Путь готов»** banner (and prefer roadmap visible above the fold / auto-scroll lightly).
5. **Session GlassIconButton** — fix double outline in native header (no extra border on glass inside headerRight; or plain Ionicons without GlassSurface border when in stack header).
6. Keep `#1/#2/#3` and Start Guide CTA (D4). No Identity/Finish.

### Slice C iterate — what landed (client, 2026-08-03)

| Piece | Where |
|-------|--------|
| softStart once | `softStartDisplay.ts` + GuideScreen: wrap only if bare; Cover title preferred (no twin softStart line) |
| Day label hygiene | `PlanOutline` + `CompactRoadmap` + `isGenericDayLabel` — skip redundant «День» kind |
| Draft footer declutter | sticky = Start Guide + tertiary «Save without starting»; Refine after clarify; version Back = text under Cover |
| Path-ready signal | Cover → outline/roadmap → «Путь готов» banner (+ light flash on false→true) → clarify below |
| Session ≡ | `GlassIconButton variant="header"` — no GlassSurface border in stack headerRight |

**Status:** C **accepted** (PO 2026-08-03). Onward → Slice D (then E).

### Slice C — what landed (client)

| Piece | Where |
|-------|--------|
| Unified Guide | `features/guide/GuideScreen.tsx` — draft + active; Cover + contract + Compact roadmap + sticky CTA |
| Compact Summaries | `features/guide/CompactRoadmap.tsx` + `buildCompactRoadmap.ts` |
| Cover / contract | `GuideCoverHeader.tsx` / `GuideContractGlance.tsx` (reuse `coverDisplay`) |
| Create → Guide | `IntentScreen` replaces into `Guide` with seed (not a different Draft UI) |
| Drawer → Guide | drafts and actives both open `Guide` |
| GuideExplore | thin alias route → same `GuideScreen` |
| Path / DraftStudio | re-export `GuideScreen` |
| Commitment (D4) | sticky **Start Guide** on Guide; no Accept duplicate map |
| Progressive create | `#1/#2/#3` poll/refine/commit preserved; **no** backend schema expansion |