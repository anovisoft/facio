---
name: facio-swiftui
description: Facio SwiftUI conventions for the iOS lid client. Use when creating, editing, or reviewing apps/mobile-swiftui, Xcode project files, or iOS UI for Facio.
---

# Facio SwiftUI

Before writing views, read:

1. This file
2. `.cursor/skills/facio-product/SKILL.md`
3. The SwiftUI expert skill (`swiftui-expert-skill`) and, for review, `swiftui-pro`

## App

- New app at `apps/mobile-swiftui`. Identity from [`docs/state/identity.md`](../../../docs/state/identity.md): `Facio`, `com.anovisoft.facio`, team `SXXLPXXJMD`, iOS 18+, portrait, no iPad.
- No third-party UI kits unless PO asks.
- Liquid Glass is on (PO, 2026-08-16): tiles and Use controls. `#available(iOS 26)` with material fallback. `GlassEffectContainer` is for a tight control cluster (Use −/+), not the lid pack — the container morphs neighbors into one blob. Lid tiles each carry their own glass. Do not invent a brand-green accent — semantic `primary` / `secondary`, tint only for meaning.
- Theme follows the system. Atmosphere is a weak gradient (not a flat fill) via `containerBackground(for: .navigation)` plus an inert window-level copy. Atmosphere never hit-tests. Whole tile opens Use (`contentShape` on the glass), not only the title row. Counter Use keeps − / + / Готово after done; tick Use uses a normal 44pt checkbox, not a hero circle. Lid tick mark is a 36pt symbol inside the tile — do not overlay glass-on-glass.
- Reminder is a **wide 4×2 row** (not 4×1): title + time + cue need a compact-tall slot or the card paints over the next tile. Matches other tiles: kebab, `.primary` title. Fire time is `ReminderClock` from the subject window, never the model. Local notification; tap opens the lid, not Use. On Use the time is a live chip from `store.windowFor` (not a compact `DatePicker` + `.constant` — that chip never redraws after save). Tap opens a **~340pt bottom sheet**: two wide `Picker` wheels (128×196, finger-sized) with a colon; **Сохранить** pinned to the bottom of the sheet, not mid-card. No title in the sheet (Use already says «успеть к»). No `DatePicker`, no `.fitted` / `.medium` / 320pt void, no second `AtmosphereBackground` on the sheet. The sheet commits `ClockTime` through a parent callback onto an `@Observable` draft (not `DatePicker`, not `.clipped` on the wheel — both drop the selection). The Use chip keeps the saved clock in `@State` so it updates even if Observation is late. `editReminderLatestBy` replaces the whole snapshot and writes the subject window even when the instance is done. Do not expand a wheel inline. Range is gym hours: default open 06:00 … `closes_at`. Do not invent `opens_at` in the schema. Use **Готово** stays the glass capsule that completes the reminder.
- Localize via `String(localized:)`. User-facing copy may be Russian; identifiers stay English and match the RFC (`Subject`, `Cue`, `Widget`, `surface`).

## Law on device

Port `packages/domain` as pure functions. Drive tests with `packages/domain/fixtures/*.json`. A mismatch with Python tests is a release hole. Do not invent a second drift or packer.

## Surfaces

- Home is one vertical lid feed. No bottom tabs. No horizontal section paging.
- Type owns tile size on a 4-column grid. Pack row-major in rank order; gaps allowed; never reorder to fill holes.
- Today / Lifetime tiles may be lightly interactive. Soon / Postponed are glance-only.
- Use: do now, no instance carousel. Inspect: carousel allowed. Left edge on fullscreen is back, not pan.
- Composer docks on the lid (and on Use — PO). Tap expands an almost-fullscreen chat sheet. Collapse hides, does not reset. New chat is at the top of the sheet.
- Chat cards are centered snapshots, not live runtimes.

## Taste

Calm table, not a casino. Prefer native SwiftUI, `@Observable`, small views, `Button` for taps. The lid is the Upwork first frame — default chrome is not enough, decoration for its own sake is not either.
