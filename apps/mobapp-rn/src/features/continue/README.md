# Continue (Facio 0.1 Slice A)

Home = **Continue**, not the Projects list.

## Guides drawer

ChatGPT-style under-sheet: Guides sits behind Continue; opening translates the main layer right (~82%). Open via ☰ or a dedicated ~28px left-edge pan strip; close via swipe left on Continue (main-layer pan) or tap peek. Motion is a single `progress` ∈ [0, 1] (snap at 0.5) — see `useGuidesRevealGesture.ts`. No RN `Modal`. Guides content is sized to the reveal width; Continue peeks as a rounded card. Theme lives in Settings (gear in Guides footer), not inline in the drawer.

## Naive order (until Slice B Focus Engine)

See `naiveOrder.ts`:

1. Active Guides with executable `next_action` first
2. Other active Guides (waiting / peek-only) after
3. Within each bucket: `updated_at` descending

Drafts are drawer-only. No Focus Engine weights yet (D1 deferred to Slice B).
