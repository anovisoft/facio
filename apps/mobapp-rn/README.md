# Facio mobile (Expo / React Native)

MVP client for [client-service](../backend-py3/client-service).

UI copy (localized): **Today / Done / Why now / Accept path** (EN) · **Сегодня / Сделано / Почему сейчас / Принять путь** (RU).

No AdMob, RevenueCat, or Firebase Analytics — UI beacons go to `POST /api/v1/events`.

## Prerequisites

1. API up from repo root:

```bash
cd ../..   # fasio/
docker compose up -d
```

2. Node 20+ recommended.

## Setup

```bash
cd apps/mobapp-rn
cp .env.example .env
npm install
npm start
```

### API URL

| Environment | `EXPO_PUBLIC_API_URL` |
|-------------|------------------------|
| iOS Simulator | `http://localhost:8000` |
| Android emulator | `http://10.0.2.2:8000` |
| Physical device | `http://<your-mac-lan-ip>:8000` |

## Auth

On first launch the app creates a UUID (`expo-crypto`), stores it in MMKV (memory fallback if native MMKV is unavailable), and sends it as `X-Device-Id` on every request. The API auto-provisions the user.

## i18n & theme

- **Languages:** English primary; Russian when the device language is `ru`; `fallbackLng: en`.
- **Theme:** `system` (default) / `light` / `dark` — switcher on the Projects screen; persisted in MMKV.

## Liquid glass FAB

Floating **+** on Projects uses [`@callstack/liquid-glass`](https://github.com/callstack/liquid-glass) when available.

| Runtime | What you see |
|---------|----------------|
| iOS 26+ **dev/production build** (Xcode ≥ 26) | Real liquid glass |
| Expo Go / older iOS / Android | `BlurView` + translucent fallback |

## Native iOS (no Expo Go)

```bash
npm run prebuild:ios   # or: CI=1 npx expo prebuild --platform ios
npm run ios            # builds + launches simulator / device
# specific sim:
npx expo run:ios --device "iPhone 17"
```

Requires Xcode (26+ for real liquid glass). Team ID for signing: `ios.appleTeamId` + `withAppleTeamId` (`SXXLPXXJMD`) — survives `prebuild`.

`expo-blur` is a library only — do **not** add it to `plugins`.

MMKV needs zlib at link time; config plugin [`plugins/withMmkvZlib.js`](plugins/withMmkvZlib.js) adds `-lz`.

Liquid glass is **not** supported in Expo Go — use this native build.

## Status

**S1:** API client, beacons, nav shell, Projects/History live.  
**S1.5:** i18n en-first, theme modes, glass FAB `+`.  
**S2:** Intent → InstantAnswer | Draft → Accept → commit.  
**S3:** ProjectHome (Сегодня / Сделано / skip / checklist / repair), Path, First Completion, loading/errors, optional Sentry.

## Optional Sentry

Set `EXPO_PUBLIC_SENTRY_DSN` in `.env`. Without it the SDK stays disabled (no-op). After adding the DSN, rebuild the native app (`prebuild` + `ios`/`android`) so the Sentry plugin is applied.

## Scripts

```bash
npm start       # Expo Go / Metro
npm run ios     # native ios (after prebuild)
npm run android
```
