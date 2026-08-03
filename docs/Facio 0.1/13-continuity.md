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
| Facio 0.1 code shell | **A+B accepted**. **Next = Slice B2** (Hero Preview + compact drawer) |
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
| `PathScreen` | → Guide roadmap |
| `DraftStudioScreen` | → GuideExplore |
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
| Cover UI | Today still on Continue + drawer cards — **B2 will move drawer to compact; Continue → Hero Preview** |

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
- **PO (2026-08-03):** drawer must become **compact nav list** (B2) — current Cover-card rows twin Continue.

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

---

## Slice status

| Slice | Name | Status |
|-------|------|--------|
| A | IA shell (nav: Continue / Session / Guide / Create / drawer) | **accepted** (PO 2026-08-03) |
| B | Focus Engine v0 + Cover on cards | **accepted** (PO 2026-08-03) |
| B2 | Hero Preview + drawer compact | **next** |
| C | Guide Explore trust (roadmap + Commitment; fold Draft) | pending |
| D | Session atom + Session complete beat + swipe/≡ | pending |
| E | Repair Diff + Undo | pending |
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

1. Read [README](./README.md) → [11](./11-success-systems.md) (§9 presentations) → **this file** → [14](./14-impl-plan.md)  
2. A+B **accepted**. Next dispatch: **Slice B2** (Hero Preview + compact drawer).  
3. B2 brief: read-only Hero; drawer compact; idle Guides off Continue; no Full Block on home; no D1–D8 invention.  
4. Do **not** reopen Guides gesture unless PO reports regress.  
5. On B2 accept → Slice **C**.
