# Facio — крышка (шаг 1)

Дом приложения — крышка: одна вертикальная лента. Сегодня первым экраном. Нет чата, сковородки, напоминаний, HTTP и модели.

Идентичность как в архиве: `Facio` / `facio` / `com.anovisoft.facio` / team `SXXLPXXJMD`. Плагин `plugins/withAppleTeamId.js` подключён в `app.config.js` — без него `prebuild` сотрёт team.

## Запуск на симуляторе или iPhone

Нужны Xcode и CocoaPods. Команды из этого каталога:

```bash
cd apps/mobile
npm install
npx expo prebuild --platform ios
npm run ios
```

`npm run ios` уже ставит `EXPO_XCODEBUILD_ARGUMENTS='-allowProvisioningUpdates'`.

На физический iPhone (тот же team, сертификаты подтянутся):

```bash
cd apps/mobile
npx expo prebuild --platform ios
EXPO_XCODEBUILD_ARGUMENTS='-allowProvisioningUpdates' npx expo run:ios --device
```

Android, если нужен:

```bash
npx expo prebuild --platform android
npm run android
```

Повторный старт не затирает живое состояние посевом. Склад — `expo-sqlite`, файл `facio.db`.

## Посев (только пустой склад)

| id | что | секция на крышке |
|----|-----|------------------|
| subject `push-ups` | ритм 3×/неделя, цель 28→30 | — |
| cue `push-ups-brace` | correction / do-time / `brace the core and the glutes` | на плитке и в Use |
| widget `push-ups-counter` | счётчик | **today** (в фикстурах закона — lifetime) |
| instance `push-ups-open` | prepared | — |
| subject `vegetables` | daily-ish 1×/день | — |
| widget `vegetables-tick` | галочка | **today** |
| instance `vegetables-open` | prepared | — |

Велосипед не сеется. Утренние дела не выдумываются.

## Плитки

Счётчик и галочка — компакт **2×2** на сетке 4 колонки. Упаковка v0: по рангу, ряд слева направо; не влезает — новая строка и дырка.

## После «готово»

- Счётчик: случай завершён, плитка уходит с Сегодня и остаётся в **Lifetime** как стоячий инструмент (можно снова открыть Use).
- Галочка: уходит с Сегодня, в Lifetime не кладётся. Возврат по ритму — не этот шаг.

## Журнал

Таблица `events` в SQLite. Типы: `cue_written`, `cue_surfaced`, `cue_applied`, `instance_started`, `instance_completed`, `counter_ticked`, `tick_toggled`. Практику при правке пальцем не удаляем.
