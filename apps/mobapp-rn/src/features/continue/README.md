# Continue (Facio 0.1)

Home = **Continue**, not the Projects list.

## Guides drawer

ChatGPT-style under-sheet: Guides sits behind Continue; opening translates the main layer right (~82%). Open via ☰ or a dedicated ~28px left-edge pan strip; close via swipe left on Continue (main-layer pan) or tap peek. Motion is finger-follow on `translateX` (px) with inertial spring settle (fling or midpoint) — see `useGuidesRevealGesture.ts`. Micro-moves ignored via `activeOffsetX`. No RN `Modal`. Guides content is sized to the reveal width; Continue peeks as a rounded card. Theme lives in Settings (gear in Guides footer), not inline in the drawer.

## Focus Engine v0 (`focusEngine.ts`)

Named product component. Ranking is deterministic (D1 in `docs/Facio 0.1/13-continuity.md`):

| Priority | Signal | Predicate |
|----------|--------|-----------|
| 1 | Overdue | `next_action.day_offset < unlocked_day_index` (catch-up debt) |
| 2 | Last day | `unlocked_day_index >= cycle.horizon_days - 1` |
| 3 | Short ≤5 min | `next_action.estimate_min != null && <= 5` |
| 4 | Others | Active Guides with executable `next_action` |
| 5 | Waiting | Active Guides without `next_action` (after all executable) |

Within a tier: `updated_at` descending. Drafts stay drawer-only. No pin Focus. No time-of-day / streak / ML weights in v0.

`rankContinueSessions(projects) → { ordered, focus, reason }` — first card is Focus; optional reason chip (`overdue` / `lastDay` / `short`) only when a top-tier signal fired.

## Cover display

Guide Cover fields (`cover_emoji`, `cover_difficulty`, `cover_duration_summary`) persist on the API. Continue cards and Guides drawer rows show emoji + difficulty · duration. When fields are null (older Guides), `coverDisplay.ts` falls back from `domain` / title / `horizon`. Server fills Cover on Path apply via heuristic (no Anthropic grammar expansion — D7 fallback path).
