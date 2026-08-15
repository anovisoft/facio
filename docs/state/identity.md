# Идентичность приложения (Apple / магазин)

Брать **как есть** из архивного клиента, чтобы сертификаты, профили и слот Expo подтянулись. Не выдумывать новый bundle / slug / team.

Источник: `archive/apps/mobapp-rn/app.config.js`.

| Поле | Значение |
|------|----------|
| Имя | `Facio` |
| Expo slug | `facio` |
| iOS bundle | `com.anovisoft.facio` |
| Android package | `com.anovisoft.facio` |
| Apple Team ID | `SXXLPXXJMD` |
| Планшеты | нет (`supportsTablet: false`) |
| Ориентация | портрет |
| Шифрование (ITS) | `usesNonExemptEncryption: false` |

На шаге 1 (крышка) скопировать `appleTeamId` и плагин `withAppleTeamId`, иначе `prebuild` сотрёт team и подпись разъедется.

На шаге 1 это обязательные поля `app.config`.
