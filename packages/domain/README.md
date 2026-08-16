# facio-domain

Закон Facio: практика, подсказка, ритм, окно, расчётный срыв, проекция крышки.  
Чистые функции, без сети и без модели.

Daily-ish моделируется как `cadence.count=1`, `cadence.period=day`. Отдельного флага нет.

Напоминание: окно несёт `latest_by`; для «зал до 22» — `window_from_closing(22:00)` → `19:00` (закрытие минус 3 часа).

## Проверки

Из корня репозитория:

```bash
python3 -m venv packages/domain/.venv
source packages/domain/.venv/bin/activate
pip install -e packages/domain
pytest packages/domain
```

Или из пакета:

```bash
cd packages/domain
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest
```

## JSON Schema

Контракт для Swift-клиента (сам Swift отсюда не генерируется):

```bash
facio-export-schema
# пишет packages/schema/*.schema.json
```

Фикстуры основателя — `fixtures/*.json`. Их гоняет и Swift-клиент. Расхождение с `packages/domain` — дыра релиза.
