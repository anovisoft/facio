# Facio API — узкий разговор

Тонкий FastAPI: одна реплика про выбранную практику → проверенный патч.  
Стол живёт на телефоне. Сервис не хранит практики и не тащит Path/Guide.

## Поднять

Из корня репозитория:

```bash
cp .env.example .env
# вписать ANTHROPIC_API_KEY
docker compose up --build
```

Сервис слушает `0.0.0.0:8000`. Остановить: `docker compose down`.  
Без ключа `POST /v1/turns` отвечает **501**. Стол на телефоне не меняется. Postgres в этот compose не входит.

Локально без Docker:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../../packages/domain
pip install -e ".[dev]"
cp .env.example .env
# вписать ANTHROPIC_API_KEY
uvicorn facio_api.main:app --reload --host 0.0.0.0 --port 8000
```

## Куда ткнуть телефон

В `apps/mobile` (или в окружении Metro):

| Где крутится приложение | `EXPO_PUBLIC_API_URL` |
|-------------------------|------------------------|
| iOS Simulator / Android emulator (host loopback) | `http://localhost:8000` |
| Живой iPhone / Android в той же Wi‑Fi | `http://<LAN-IP-мака>:8000` |

Пример для симулятора:

```bash
cd apps/mobile
echo 'EXPO_PUBLIC_API_URL=http://localhost:8000' > .env
npx expo start
```

Ключ Anthropic в приложение не кладётся.

## Ход

`POST /v1/turns`

```json
{
  "utterance": "поясница забирает нагрузку",
  "subject": { "...": "Subject" },
  "cues": [],
  "widget": { "...": "focused Widget" }
}
```

- **200** `{ "confirmation": "...", "patches": [ ... ] }`
- **422** патч невалиден (нет `surface`, рост цели/ритма при боли, плохой JSON модели)
- **501** нет `ANTHROPIC_API_KEY`

Контекст модели: только focused subject + его cues + виджет + реплика.

## Ops

| op | смысл |
|----|--------|
| `add_cue` | `kind`, `text`, `surface` обязателен; correction → do-time, clarification → on-demand |
| `set_target` | `goal`, опционально `current` |
| `set_cadence` | `count >= 1`, `period` day\|week |
| `shrink` | `cadence`: `{count:1, period:"week"}` или `"none"` |
| `none` | объяснение без мутации |

Политика боли применяется в питоне на патче, не «пожалуйста» в промпте.

## Золотые проверки

Без ключа и без сети:

```bash
cd apps/api
source .venv/bin/activate
pytest
```
