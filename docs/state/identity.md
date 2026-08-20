# Идентичность приложения (Apple / магазин)

Брать **как есть** из архивного клиента, чтобы сертификаты и профили подтянулись. Не выдумывать новый bundle / team.

Источник: `archive/apps/mobapp-rn/app.config.js`.

| Поле | Значение |
|------|----------|
| Имя | `Facio` |
| iOS bundle | `com.anovisoft.facio` |
| Apple Team ID | `SXXLPXXJMD` |
| Планшеты | нет |
| Ориентация | портрет |
| Шифрование (ITS) | `usesNonExemptEncryption: false` |
| Минимум iOS | 18.0 |

Expo slug больше не нужен. Display name и bundle на шаге 1 зашить в Xcode-проект, иначе подпись разъедется.

Вход v1 (Q19, PO 2026-08-20): Sign in with Apple на этом Team ID. Google не подключать, пока нет второй платформы.
