# Continue (Facio 0.1)

Home = **Continue** — Focus-ranked **Hero Previews** of Sessions that need attention.  
Guides drawer = **compact inventory**, not a second Continue.

Product stack: Guide = path · Continue = focus · Session = Full Block execute · Drawer = nav.

## Guides drawer (compact)

ChatGPT-style under-sheet: Guides sits behind Continue; opening translates the main layer right (~82%). Open via ☰ or a dedicated ~28px left-edge pan strip; close via swipe left on Continue (main-layer pan) or tap peek. Motion is finger-follow on `translateX` (px) with inertial spring settle — see `useGuidesRevealGesture.ts`. No RN `Modal`.

**B2 compact rule:** each row is emoji/mark + title (+ thin `Draft` / `Waiting` status). No Cover difficulty · duration twin cards. Archive + Settings gear stay in the footer. Tap → Guide trust surface (draft or active — same Cover + roadmap chrome; Slice C).

## Attention filter (B2)

Continue shows only Sessions that **need attention**:

- `status === 'active'` **and** executable `next_action != null`
- Idle / waiting Guides (`next_action == null`, peek-only) → **drawer only**
- Drafts → drawer only

Empty Continue while open Guides exist in the drawer is OK (`continue.emptyAttention`).

`needsAttention(project)` + `rankContinueSessions` in `focusEngine.ts`.

## Focus Engine v0 (`focusEngine.ts`)

Named product component. Ranking is deterministic (D1 in `docs/Facio 0.1/13-continuity.md`) over the **attention set**:

| Priority | Signal | Predicate |
|----------|--------|-----------|
| 1 | Overdue | `next_action.day_offset < unlocked_day_index` (catch-up debt) |
| 2 | Last day | `horizon_days > 1` AND `unlocked_day_index >= horizon_days - 1` (1-day Guides excluded) |
| 3 | Short ≤5 min | `next_action.estimate_min != null && <= 5` |
| 4 | Others | Remaining attention candidates |

Within a tier: `updated_at` descending. No pin Focus. No time-of-day / streak / ML weights in v0.

`rankContinueSessions(projects) → { ordered, focus, reason }` — first card is Focus; optional reason chip (`overdue` / `lastDay` / `short`) only when a top-tier signal fired.

## Hero Preview (`heroPreview/`)

Read-only fragment of the current Session Block for Continue. **Not** a shrunk Full Block — separate views; do **not** import interactive plugin controls from `ActionPlugins`. Entire card Pressable → Session (Full Block).

| Block kind | Hero shows |
|------------|------------|
| **checklist** | Session title + up to 5 items with ☐/☑ + `N/M` + ≈min |
| **stepper** | Session title + beat hint `1/N · kind · counter|clock` (+ beat title) + ≈min |
| **timeline** | Session title + duration clock · marker count + ≈min |
| **timer** | Session title + first timer clock · title or timer count + ≈min |
| **fallback** | Session title + block type label (intervals / counter / hints / plain) + ≈min |

Guide Cover emoji is a **small context mark** only; the card object is the **Session** (`next_action.title`), not Guide Cover meta.

Detection: `detectHeroBlockKind` — stepper → timeline → timers → checklist → fallback.  
Helpers: `formatApproxMin`, `formatClock`. Entry: `HeroBlockPreview`.

## Cover display

Guide Cover fields (`cover_emoji`, `cover_difficulty`, `cover_duration_summary`) persist on the API. Continue uses emoji as a thin context mark; Cover difficulty · duration belong on **Guide page** (`GuideCoverHeader` + contract glance + Compact roadmap — Slice C), not as Continue/drawer card bodies. When emoji is null, `coverDisplay.ts` falls back from `domain` / title. Server fills Cover on Path apply via heuristic (D7 fallback — no Anthropic grammar expansion).

## Guide trust surface (Slice C)

`features/guide/GuideScreen.tsx` — one surface for draft + active:

- Cover + contract glance + Compact Summaries roadmap (`CompactRoadmap` / `buildCompactRoadmap`)
- Pre-commit sticky **Start Guide** (commit → Session); clarify/refine preserved
- Post-commit sticky **Start Session** when `next_action` exists
- PathList only behind secondary “View full plan” expand (not the hero)
- Progressive create `#1/#2/#3` unchanged on the client poll/commit path; backend schemas untouched

## Session execute (Slice D)

`features/home/ProjectHomeScreen.tsx` — Full Block + atom:

- Layout: **title → Day N/M (if `horizon_days > 1`) → large Block → detail / why** (Why demoted)
- Done → if same Guide still has `next_action` → stay on Session (light «Next: …» flash); else → **Continue**. No modal / progress bar.
- ≡ (`GlassIconButton variant="header"`) → Guide with `fromSession: true` (swipe-up removed). Back from Guide = sticky **Back to Session** / stack back.
- Same-day Block runtime: MMKV/`useSessionStore.blockRuntimeByActionId` keyed by `actionId` + local date (D2). Stepper beatIndex (+ rest wall-clock) hydrates on remount; cross-day expires. Counters remain server-backed.
- Stepper: Back + Next; rest cleared on step back.
