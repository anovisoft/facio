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
- Liquid Glass is on (PO, 2026-08-16): tiles, Use controls, grouped in `GlassEffectContainer`. `#available(iOS 26)` with material fallback. Do not invent a brand-green accent — semantic `primary` / `secondary`, tint only for meaning.
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
