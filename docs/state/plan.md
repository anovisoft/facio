# План реализации

Порядок из RFC (вопрос 23), уточнённый 2026-08-16.  
Продуктовые фазы клина — в [00](../rfc/00-vision.md). Здесь — инженерные шаги.

Правило: не прыгать через шаг без явной причины. Шаги 0–5 приняты (5 на минималках). Дальше — волны **В1–В3** (принят PO, 2026-08-20): рот → неделя/пауза локально → база и облако. **В1.0–В1.6 готовы. В2.1–В2.2 готовы.** Дальше **В2.3**. Не говорить «В2 готов». RFC не переписывать под фичу; пауза — принятый кусок волны, статус `paused` дописан в [04](../rfc/04-domain-model.md) / tools в [05](../rfc/05-ai-and-memory.md).

---

## Шаги

### 0. Закон

**Зачем.** Арифметика до пикселей.

- Модели: практика, подсказка, случай, виджет, ритм, окно.
- Чистые функции: срыв, проекция крышки, время напоминания.
- Фикстуры основателя. Подсказка без места показа — отказ.

**Не входит.** Сеть, экраны, модель.

**Статус: принят.** `packages/domain`, проверки зелёные.

### 1. Крышка на устройстве

**Зачем.** Фаза 0 зрения: одна практика держит причину. Первое впечатление для витрины.

- Новое SwiftUI-приложение. Дом — крышка, одна лента сверху вниз.
- Склад на устройстве. Сразу журнал событий, не только снимок виджета.
- Swift-порт закона на **тех же** фикстурах, что `packages/domain/fixtures`.
- Заготовка руками: отжимания `3×/неделя`, цель 30, подсказка «корпус и ягодицы»; овощи «почти каждый день».
- Счётчик: число и подсказка на плитке в момент дела. Галочка. Use без карусели и без свайпа вчера.
- Сетка в четыре колонки, упаковка простая: по рангу, дырки можно.

**Не входит.** Поле разговора, сковородка, напоминания, сервер, список практик.

**Готово когда.** Открыл → видишь отжимания → на первом повторе читается подсказка. Крышку не стыдно поставить первым кадром записи.

**Статус: принят** (PO, 2026-08-16).

### 2. Напоминание и окно

- Практика «велосипед», подсказка времени «зал до 22» → окно «успеть к 19:00».
- Локальное уведомление из объекта напоминания, не из модели.
- Нажатие ведёт на крышку.

**Статус: принят** (PO, 2026-08-16). Посев и старый стол получают велосипед. Плитка-ряд 4×2, Use, локальный пуш из `ReminderClock`, час на Use: чип → sheet (колёса час/минута + Сохранить). Тап пуша открывает крышку.

Посев с уже висящим 19:00 **не ломаем**. Новые практики из рта (волна 1) сначала **без** напоминания — см. замки ниже.

### 3. Срыв и утренняя карточка

- Утро: сдвиг или срыв → максимум одна карточка на сегодня.
- Чипы только вниз. **Лестница (R4, принята PO 2026-08-30):** карточка рисует одну ступень — «сегодня», затем «раз в неделю», затем «убрать» — плюс «не сейчас». Не три чипа сразу: иначе отказ нечем выразить и Q28 «замолчать после двух отказов» не срабатывает никогда.
- Пустой сегодня без срыва остаётся пустым.

**Статус: принят** (PO, 2026-08-16). Карточка на Сегодня, чипы только вниз. Посев без живой активности велосипеда: 21 день тишины, плитка в Lifetime, пока карточка жива. Чипы: высота 32, ширина по тексту до 152, многоточие, перенос ряда. Утренний пуш не делался — нет часа в RFC. Дельта-утро **сделано** (R4): карточка на дельте или срыве, максимум одна.

### 4. Разговор

Труба и рот в одном шаге: без рта клин нельзя показать чужому и нельзя снять для витрины.

1. Стенд золотых реплик → ожидаемые вызовы и конечный стол. Не украшение.
2. FastAPI: ход в текущий тред, проверенный патч. Ключ только на сервере.
3. Инструменты ровно из [05](../rfc/05-ai-and-memory.md).
4. Поле на крышке (и на Use — решение PO) → почти полный лист. Свернуть ≠ новый тред. «Новый чат» справа сверху.
5. Смена схемы — живая плитка и снимок по центру. Только объяснение — текст.
6. Политика боли до инструментов.

Склад на этом шаге ещё может быть только на устройстве. Сервис принимает снимок стола и возвращает проверенный патч.

**Готово когда.** «Поясница забирает» → подсказка на отжиманиях, плитка живая, это видно на записи ~90 секунд.

**Статус: принят** (PO, 2026-08-19). FastAPI `POST /v1/talk/turn`: снимок стола + реплика → проверенный патч. Золотые в `apps/api/goldens`. Рот: док на крышке и Use (`facioComposerDock` на экранах, не на стеке — иначе «Готово» под доком), лист почти на весь экран, «Новый чат» справа сверху, collapse не сбрасывает тред. Поле листа однострочное, заглушка по вертикальному центру. «Поясница забирает» пишет do-time подсказку на отжимания («не поясницу», чтобы плитка отличалась от посева) и снимок в чат. Ключ только на сервере; без ключа — scripted. Живая модель: `FACIO_MODEL_NAME` (`gpt-4o-mini` или `haiku`), ключи `FACIO_OPENAI_API_KEY` / `FACIO_ANTHROPIC_API_KEY` по отдельности необязательны. Локально: `docker compose up --build` из корня.

### 5. Сковородка, список практик, просмотр

После живого клина. Жест от левого края. Делать ≠ смотреть. Плюс создаёт новый случай.

**Статус: принят PO на минималках** (2026-08-19). Сковородка только с корня крышки (☰ + жёлоб 20pt на `LidScreen`). `PanSlideLayout`: закрытая крышка = весь экран; открытая — карточка, скругление экрана. «Facio» в ленте с `pagePadding`. Шторка ниже статус-бара (`WindowMetrics.safeArea`). Use/Inspect: левый край = назад. Talks — архив в сковородке. Deeds → кебаб. Inspect ≠ Use. Плюс создаёт случай. Кебаб урезан (PO ок); зажатие плитки = кебаб. Настройки — подпись. Док рта на Inspect нет.

**Рефактор костылей** (2026-08-19, поведение то же). Геометрия в `PanSlideLaw`, окно в `WindowMetrics`, title в `facioLidTitle()`, лист рта после кебаба через `onDismiss`. Несущие костыли оставлены: пустой `principal`, `compositingGroup`, UIKit окно, `LongPressTapLock`, клавиатура, две атмосферы. Не шаг 6. Не воскрешать `HStack`+offset, `safeAreaPadding(.leading)`, `if revealed > 0` на dim, `zIndex` шторки выше крышки, `GeometryReader` вокруг стека.

**PO, вечер 2026-08-19.** Текущий концепт крышки/шторки принят как опробованная гипотеза («выглядит удобно»). Не полир.

**PO, ночь 2026-08-20.** Цель шире прежнего Р.1–Р.5: метод 4→30 средним текстом с приземлением в инструменты; чтение стола; позже календарь на 7 дней, пауза по боли, база, облачный пуш. RAG не в первой волне. Напоминание не вешается на зал при создании.

### Волны после клина (принят PO, 2026-08-20)

Не новый номер в Q23. Черновик **Р.1–Р.5** (2026-08-19) **снят** этим текстом. Пользователь «MCP» не слышит. Сущности «план / Guide / Path» не заводим: CRUD = практика + виджет + ритм + подсказка.

Принят PO 2026-08-20. Ведёт **PM**; субагенты — разработчики, скилы по `AGENTS.md`. **В1.0–В1.6 готовы** (В1.4 принят PO; час 19 vs 20 принят PO). **В2.1–В2.2 готовы.** Дальше **В2.3**. Не прыгать в В3.

«Таймер» в этой цели — **напоминание** (виджет `reminder` + окно), не countdown `timer`. Countdown по-прежнему пустой тип на крышке.

#### Замки

- Крышка, тики, срыв, **час выстрела** — без LLM. Модель предлагает факт или явную просьбу; `set_reminder` и развёртка слотов считают сами.
- Вывод текстом без механики — баг. Средний ответ «как до 30» в том же ходе вызывает инструменты (цель, ритм, подсказка).
- Боль не растит цель и ритм. Пауза «пока спина» — не рост и не «постарайся».
- **Зал / практика сначала без напоминания.** Виджет напоминания появляется только если: (а) человек сказал, что не сходил / пропустил, и вывод хода — нужен час; или (б) сам попросил час. Посев шага 2 (велосипед уже с 19:00) не трогаем.
- Два факта про час, не путать:
  1. «зал до 22» → `window_from_closing` → 19:00. Только когда факт **произнесли**, не при создании практики.
  2. «напомни в 19, в 21 я уже сплю» → `latest_by = 19:00` **как сказано**. Не вычитать 3 часа из 21 (получилось бы 18:00). Сон — `timing` cue, не формула двери зала.
  3. Назвали и дверь, и час («к 23 закрывается, в 19 часов») → `latest_by` как сказали (19:00). `closes_at` — дверь. Не 23−3 = 20:00. Формула только если час **не** называли.
- Дом — крышка (сегодня), не недельная сетка. 7 дней — проекция на Inspect, не второй дом.
- Память v1 — подсказки с `surface`. Корпус спорта и сырая переписка в индекс не идут. Поиск по своим фактам — только В3.
- **Бекенд в этих волнах — сервис, не стенд из нескольких файлов.** Сейчас `apps/api` — клин шага 4: один роутер, `turn` + `provider` + золотые. Этого мало для MCP, аккаунта, стола и пуша. Растить `facio_api` по волнам (роутеры, провайдеры, MCP, тесты). Закон остаётся в `packages/domain`. `.cursor/skills/fastapi-templates/` **не копировать в В1–В2** (там сразу БД, JWT, CRUD). **В3 можно** взять из него сессию Postgres, репозитории аккаунта/стола — в том же пакете, без брокера «на вырост» и без второго процесса. Крышка без сети тикает.

#### Зазор

**Уже есть.** `POST /v1/talk/turn`; 16 имён RFC 05 в `apply_tool`; боль до apply; founding + В1.2 золотые; док на Lid/Use; стол на устройстве; локальный пуш; MCP stdio (`python -m facio_api.mcp`). `create_widget` отказывает `checklist`/`timer`/`stepper` (`unsupported_widget_type`) до append. `set_reminder` создаёт виджет reminder 4×2, если его не было. Крышка декодирует `tool_calls`; `applyTalk` не откатывает running count.

**По волнам.** В1: каркас сервиса (не дописывать в `main.py`) + метод 4→30 + чтение стола + зал без часа + час только по пропуску или просьбе. В2: развёртка ритма на 7 дней + заморозка + локальный чек-ин через 2 дня; API готов принять слоты/паузу, база ещё не обязательна. В3: полноценный сервер записи — аккаунт Apple, Postgres, синк стола, воркер пуша, поиск по своим фактам.

**Режем, пока PO не скажет иначе.** Countdown-рантайм, каталог упражнений, RAG-корпус спорта, голос, готовка, `generation`, полир шторки, док на Inspect, Expo / `archive/`, переписывание RFC.

**Распарковано PO 2026-08-29** (цель «дойти до RFC-версии»): кебаб 3×4 и postpone/delete, реальные Настройки, select→clarification, дельта-утро. Media на cue — в очереди (R6).

#### MCP и HTTP

Обёртка над talk в том же `apps/api`, не второй compose-сервис. Телефон всегда HTTP: `GET /v1/health`, `POST /v1/talk/turn`. Live GPT/Haiku — function calling. MCP — второй рот к `apply_tool`. Стол до В3 едет снимком в ходе.

```text
телефон -- HTTP /v1/talk/turn --> facio_api -- function calling --> apply_tool
Cursor/агент -- MCP (тот же процесс) ---------------------------------^
```

Новые имена — только с золотыми той волны (Q22). В1 новых имён нет. В2.3 добавляет `freeze_subject` / `thaw_subject` **вместе** с золотыми.

Целевая нарезка `apps/api` (один пакет, один деплой, не флот):

```text
facio_api/
  main.py                 # factory, include_router
  config.py
  routers/                # HTTP: health, talk; позже auth, desk, devices
  talk/                   # ход, схемы, spec инструментов, золотые
  providers/              # scripted / openai / anthropic
  mcp/                    # В1.3, тот же apply_tool
  accounts/               # В3, Sign in with Apple
  desk/                   # В3, сервер записи снимка
  jobs/                   # В3, APNs / расписание
```

Тесты: `tests/unit` и `tests/integration` (httpx к приложению). В1 без БД. Закон и арифметика не мокаются.

---

#### Волна 1 — рот на устройстве

Стол локальный. Нет Postgres, нет RAG, нет облачного пуша, нет сетки недели. Пакет API уже не «восемь файлов в куче».

##### В1.0 — Каркас сервиса

**Зачем.** Иначе золотые, MCP и live свалятся в `turn.py` / `main.py`. Дальше В3 некуда класть аккаунт и стол.

**Статус: готов** (2026-08-20). `create_app()`, health и talk на разных роутерах, `talk/` + `providers/`. Три founding-золотые зелёные. Старых shim-модулей нет.

**Входит.** Разнести текущий `facio_api` по `routers` / `talk` / `providers`. `FastAPI` через factory. `Depends` на настройки. Health отдельно от хода. Pytest как сейчас зелёный. Контракт телефона тот же: `GET /v1/health`, `POST /v1/talk/turn`.

**Не входит.** Postgres. Auth. Очереди. Шаблон `fastapi-templates` (он для В3). Новые URL для телефона. Смена поведения золотых. Пустые пакеты `mcp/` / `accounts/` / `desk/` / `jobs/`. В1.1+. Крышка.

**Готово когда.** Каталог модулей читается как сервис; ход рта и три founding-золотые без регрессии.

**Золотые.** Старые три не трогать (`apps/api/goldens/*.json`).

**Контракт (PM, 2026-08-20).** Поведение рта не менять — только нарезка.

Сейчас (стенд шага 4): `facio_api/{main,config,provider,turn,schemas,spec,goldens}.py`; тесты `tests/test_providers.py`, `tests/test_goldens.py`, `tests/integration/test_talk_api.py`.

Цель:

```text
facio_api/
  main.py                 # create_app() → include routers; app = create_app()
  config.py               # Settings без смены полей; get_settings
  routers/
    health.py             # GET /v1/health, tag health
    talk.py               # POST /v1/talk/turn, tag talk
  talk/
    loop.py               # run_turn, TalkError
    schemas.py
    spec.py               # SYSTEM_PROMPT без правок текста
    goldens.py            # load/match; JSON остаются в apps/api/goldens
  providers/
    types.py              # Protocol + ModelTurn / ModelToolCall / LiveProviderError
    scripted.py
    openai.py
    anthropic.py          # перевод OpenAI-shaped messages/tools
    factory.py            # provider_for
```

Замки нарезки:

- Uvicorn / Dockerfile / `[tool.fastapi] entrypoint` остаются `facio_api.main:app`.
- Старых модулей `turn.py` / `provider.py` / `schemas.py` / `spec.py` / `goldens.py` в корне пакета **не оставлять** (без shim).
- `goldens_dir()`: `FACIO_GOLDENS_DIR` или `apps/api/goldens` от корня пакета `facio_api` (`Path(facio_api.__file__).parents[2] / "goldens"`), не `parents[N]` файла `goldens.py`.
- Тесты: `tests/unit/` (провайдеры, золотые, factory) и `tests/integration/` (httpx к приложению). Импорты на новые пути. Monkeypatch `httpx.AsyncClient` на модуль, который ходит в сеть (`providers.openai` / `providers.anthropic`).
- Добавить: `create_app()` собирает приложение; health и talk — **разные** `APIRouter`; пути те же. Не мокать закон.
- `Depends(get_settings)` как сейчас. `Annotated`. Не тащить SQLModel / брокер / `fastapi-templates` (шаблон — В3).
- Не трогать: `packages/domain`, `apps/mobile-swiftui`, `docs/rfc`, `archive/`, compose URL, поля `Settings`, имена tools, текст `SYSTEM_PROMPT`.

##### В1.1 — Пустые типы не пишутся

**Зачем.** `create_widget(type=timer)` проходит и исчезает с крышки.

**Статус: готов** (2026-08-20). `create_widget(checklist|timer|stepper)` → `unsupported_widget_type`, стол не меняется. Счётчик/галочка без авто-напоминания; reminder по явному вызову.

**Входит.** Отказ apply на `checklist` / `timer` / `stepper`. `reminder` разрешён, но не создаётся сам при `create_widget` счётчика/галочки. Три старые золотые зелёные.

**Не входит.** Рантаймы этих типов. UI. MCP. Новые золотые реплики. Правка `SYSTEM_PROMPT`. В1.2.

**Готово когда.** Пустой тип не мутирует стол; counter / tick / reminder по явному вызову — да.

**Золотые.** Новых реплик нет.

**Контракт (PM, 2026-08-20).** Закон, не HTTP.

- Гейт в `packages/domain` `_create_widget`, **до** append субъекта/инстанса/виджета. `apply_tool` при `ToolFail` и так возвращает исходный стол.
- Пустые типы: `checklist`, `timer`, `stepper` → `ok=False`, `mutated=False`, `desk` is исходный, `error=unsupported_widget_type` (новая константа рядом с `INVALID`, не сырой `"invalid"`).
- Имена tools и enum в схеме/спеке **не** сужать: модель может вызвать, apply отказывает. `packages/schema` и RFC не трогать.
- `create_widget(type=counter|tick)` — пишет этот виджет; **не** дописывает `reminder`.
- `create_widget(type=reminder)` и `set_reminder` — как сейчас. Посев велосипеда с 19:00 не ломать.
- Тесты: `packages/domain/tests/test_tools.py` (parametrized пустые типы; counter/tick без reminder; reminder явный). Прогон ещё `apps/api` pytest — три founding без регрессии.
- Не трогать: `apps/mobile-swiftui`, `docs/rfc`, `archive/`, `apps/api/goldens/*.json`, `talk/spec.py`, `talk/loop.py`.

##### В1.2 — Золотые метода, чтения и часа по просьбе (Q22)

**Зачем.** Открыл рот → «умею 4, хочу 30» → средний текст как → в конце хода инструменты. Зал без напоминания, пока не пропуск и не «напомни в 19».

**Статус: готов** (2026-08-20). Шесть золотых + неизвестная реплика без патча. `update_widget` пишет current из count; `set_reminder` создаёт виджет, если его не было.

**Входит.** JSON в `apps/api/goldens`, scripted + pytest. Для «зала без часа» — стол **без** reminder у этой практики (посев с 19:00 не есть ожидаемый результат этого хода).

1. Метод: «могу 4, хочу 30 подряд, как?» → средний `text` + в том же ходе `list_desk` или `get_*`, затем запись: цель 30, current 4 если ещё не 4, ритм, `add_cue` do-time (короткая команда, не лекция поверх). Снимок в чате. Текст без мутации — провал.
2. Зал/практика из рта без часа: создание или обсуждение **не** вызывает `set_reminder` и не добавляет виджет `reminder`.
3. Пропуск: «сегодня не сходил» → можно `skip`; `set_reminder` только если вывод хода — повесить час (не на любую реплику пропуска).
4. Явная просьба: «напомни в 19, в 21 я уже сплю» → `set_reminder` с `latest_by=19:00` (не 18:00), timing-cue про сон. Пуш из объекта, не из модели.
5. «зал до 22» — если произнесли **этот** факт → 19:00 арифметикой. Не пришивать к созданию.
6. Боль+рост: старый `pain_raise` остаётся. Ужать ритм через рот — `times_per_week` не растёт.

**Не входит.** Заморозка на дни. Сетка 7 дней. Live CI (В1.5). Новые имена tools. Countdown. Крышка (В1.4). MCP (В1.3).

**Готово когда.** Scripted прогон старых трёх + этих; неизвестная реплика без патча.

**Контракт (PM, 2026-08-20).**

Стол золотых — `founding_desk` (отжимания цель 30 / current 28, велосипед уже с 19:00). `match_golden` берёт **первый** файл по sort имени — иглы не должны пересекаться.

**Закон (узко, без новых имён):**

1. `update_widget`: если передан `count` и тип счётчик — пиши `subject.target.current` (цель не трогать, если `target` не передали). Иначе «current 4» на push-ups не приземляется.
2. `set_reminder`: если у субъекта **нет** виджета `reminder` — создай его (`4x2`, `fire_at` из окна). Иначе «напомни в 19» / «зал до 22» на новой практике не даст ряд. Не создавать reminder из `create_widget` счётчика/галочки (В1.1 держать).

**Промпт.** В `SYSTEM_PROMPT` заменить строку про «зал до 22» на:

```
- Срыв и час напоминания не считай. Новую практику не снабжай reminder и не вызывай set_reminder, пока человек не попросил час или не сказал, что пропустил и нужен час.
- «зал до 22» — только если этот факт произнесли: set_reminder closes_at, окно само даст 19:00.
- «напомни в 19, в 21 сплю» → set_reminder latest_by как сказали (19:00), не вычитай из 21. Сон — timing cue.
```

Остальной текст промпта не переписывать.

**Файлы золотых** (не править `lower_back` / `pain_raise` / `explain_only`):

| id / файл | utterance | match (подстроки) | scripted (порядок) | expect |
|---|---|---|---|---|
| `method_4_to_30` | могу 4, хочу 30 подряд, как? | `могу 4`, `хочу 30 подряд` | 1) `list_desk` или `get_widget`/`get_subject` на push-ups 2) `update_widget` push-ups-counter `target=30` `count=4` 3) опционально `set_cadence` count≤3 4) `add_cue` do-time, текст ≠ посев «держи корпус и ягодицы», короткая команда 5) средний `text` (≥2 предложения) | mutated; current=4; goal=30; снимок; нет reminder-вызовов; `times_per_week` не вырос |
| `gym_no_clock` | запиши зал | `запиши зал` | `create_widget` type=counter, новый `subject_id` (не bike/push-ups/vegetables) | mutated; у **этого** субъекта 0 виджетов reminder; в tool_calls нет `set_reminder`; велосипед с 19:00 на месте |
| `miss_skip` | сегодня не сходил | `сегодня не сходил` | `skip` (bike-reminder); **нет** `set_reminder` | mutated; skip ok; latest_by велосипеда всё ещё 19:00 |
| `remind_at_19` | напомни в 19, в 21 я уже сплю | `напомни в 19` | `set_reminder` bike `latest_by=19:00` (не 18:00, не closes_at 21); `add_cue` surface=timing, текст про сон | mutated; `window.latest_by==19:00`; timing-cue; не 18:00 |
| `gym_until_22` | зал до 22 | `зал до 22` | `set_reminder` bike `closes_at=22:00` (арифметика, не latest_by вручную 19) | mutated; latest_by 19:00; closes_at 22:00 |
| `cadence_shrink` | давай раз в неделю | `давай раз в неделю` | `shrink_subject` или `set_cadence` period=week count=1 на push-ups | mutated; `times_per_week` ≤ 1; цель не выросла |

Неизвестная реплика (без JSON): «квэкснутый зонд 174» → `mutated is False`, tool_calls пуст. Игла не должна матчить золотые.

**Тесты.** Расширить `apps/api/tests/unit/test_goldens.py` (и `test_goldens_are_present`). Domain-тесты на current=4 и upsert reminder, если трогали закон. Три founding зелёные.

**Не трогать:** `apps/mobile-swiftui`, `docs/rfc`, `archive/`, имена tools, compose, В1.3+.

##### В1.3 — MCP-адаптер, те же 16 имён

**Зачем.** Список / подробное чтение / CRUD виджетов для агента = уже существующие tools.

**Статус: готов** (2026-08-20). `DeskSession` + stdio `python -m facio_api.mcp`. Те же 16 имён. `/v1/talk/turn` без изменений.

**Входит.** MCP в том же пакете `apps/api`; вызов = `apply_tool`; стол = снимок в сессии. Тест: `list_desk` + `add_cue` совпадают с прямым apply. Compose — один `talk`.

**Не входит.** База. Auth. Замена HTTP телефона. Новые URL для телефона (`/v1/*` как есть). `search_*`. Календарные tools. 17-е имя. HTTP-mount `/mcp` (stdio достаточно). Крышка. В1.4+.

**Готово когда.** Адаптер локально отвечает списком tools и одним write; `/v1/talk/turn` не изменился.

**Золотые.** В1.2 зелёный.

**Контракт (PM, 2026-08-20).** Пользователь «MCP» не слышит — никакого копи на крышке.

```text
facio_api/mcp/
  session.py    # DeskSession(desk, now, pain=False) → apply_tool
  server.py     # MCP stdio, имена из TOOL_NAMES
  __main__.py   # python -m facio_api.mcp
```

- `DeskSession.call(name, arguments)` → `apply_tool` с `origin=CueOrigin(chat_id="mcp")`. После успешного/неуспешного вызова `session.desk` = `outcome.desk` (как talk: fail не оставляет полузапись — apply уже откатывает).
- Имена ровно `facio_domain.tools.TOOL_NAMES` (16). Схемы — из `tool_schemas()`, не второй каталог.
- Стол в сессии, не аргумент `desk` у RFC-tools (это было бы новое поле). Тесты создают `DeskSession(founding_desk())`.
- `pain=False` по умолчанию (боль — у хода рта, не у агента без реплики).
- stdio: официальный пакет `mcp` (не FastMCP-зоопарк, не второй контейнер). Compose не трогать. Dockerfile CMD без изменений.
- Тесты `apps/api/tests/unit/test_mcp.py`: (1) `session.names() == list(TOOL_NAMES)`; (2) `list_desk` data == прямой `apply_tool`; (3) `add_cue` на push-ups do-time → тот же cue id/text/surface и `mutated`, что прямой apply. Не мокать закон.
- Не трогать: `talk/loop.py`, золотые JSON, `SYSTEM_PROMPT`, Swift, RFC, `accounts/`/`desk/`/`jobs/`.

##### В1.4 — Клиент без полира

**Зачем.** На крышке видно приземление метода; напоминание не появляется, пока не прошёл ход 3 или 4 из В1.2.

**Статус: принят PO** (2026-08-20 вечер). Scripted на симуляторе: 4→30, «запиши зал» без ряда, «напомни в 19» → 19:00 не 18:00. Микро замечания к UI — **парковка**, не полир, пока PO не даст список. `applyTalk` не откатывает running count, если рот не писал этот виджет. `tool_calls` декодируются. Док не трогали.

**Входит.** Симулятор + `scripted`. Починить только если `applyTalk` ломает сценарии. Док не трогать.

**Не входит.** Полоса недели. Select. Голос. Inspect-док. Полир шторки. Live CI (В1.5).

**Готово когда.** На записи: 4→30 меняет плитку; новый зал без ряда-напоминания; после «напомни в 19» ряд 4×2 и локальный пуш.

**Мина.** `applyTalk` = полная подмена стола. Точечный фикс «не откатывать running count», не синк.

**Контракт (PM, 2026-08-20).** Крышка, не API.

Факт: `TalkTurnResponse` на проводе уже несёт `tool_calls`, клиент их **не декодирует** — `applyTalk` слепо кладёт весь стол. Пока человек тикает счётчик, ответ рта с add_cue откатывает `payload.count`.

1. Декодировать `tool_calls` (`name`, `arguments`, `ok`, `error`) в `TalkTurnResponse`. Старый JSON без поля — пустой список.
2. `applyTalk(_ desk:toolCalls:)`: `commit(reminders: true)` как сейчас. Перед записью: для виджета, который **локально** `.running`, сохранить `payload.count` и `.running`, **если** ни один успешный `update_widget` / `create_widget` не трогал этот `widget_id` (из `arguments["widget_id"]` / `arguments["id"]`). Иначе метод 4→30 не приземлит count=4.
3. Тесты в `DeskStoreTests` (без UI):
   - tick 28→29 running; incoming стол с count=28 и tools=`add_cue` → остаётся 29 running, cue пишется.
   - local running 29; incoming count=4 и успешный `update_widget` на `push-ups-counter` → 4.
   - incoming новый counter `subject_id=gym`, без reminder-виджета → у gym нет reminder; bike-reminder на месте.
   - incoming `set_reminder` на субъект без reminder (овощи или новый) → есть виджет type reminder `tileSize` 4×2.
4. `TalkSheet` передаёт `response.toolCalls`. Док (`facioComposerDock`) не трогать.

Не трогать: `apps/api` золотые/loop, `packages/domain`, pan layout, Inspect, RFC, archive. Не полир.

Готово для PO-записи когда тесты зелёные: scripted Compose + симулятор, реплики из В1.2.

##### В1.5 — Live-harness

**Зачем.** Scripted золотые не ловят, что живая модель нарушила замки (зал с часом, 18:00 из «сплю в 21», текст без патча).

**Статус: harness готов** (2026-08-20). Первый live-прогон: **3 passed / 5 failed**. Провал — промпт (текст без tools), не набор имён. `SYSTEM_PROMPT` не трогали.

**Входит.** Маркер `live`; `pytest -m live` бьёт в вендора; без ключа — skip. Инварианты стола из В1.2, не `expect.tools` и не дословный `text`.

**Не входит.** Правка золотых JSON. Правка `SYSTEM_PROMPT` (провал live — репорт PM, не «подкрутить промпт»). Новые имена tools. Swift. Compose. В2. CI-облако.

**Готово когда.** Обычный `pytest` в `apps/api` зелёный и **не ходит в сеть**, даже если `.env` с ключом. `pytest -m live` без ключа — все skip. С ключом — инварианты ниже.

**Live-прогон (2026-08-20).** Тесты форсят `talk_mode=live`. Ключи из корневого `.env` и `apps/api/.env`.

| реплика | live |
|---|---|
| могу 4, хочу 30 подряд, как? | fail: `mutated is False`, tools пусты |
| запиши зал | fail: уточняет текстом |
| сегодня не сходил | fail: спрашивает, `skip` нет |
| напомни в 19, в 21 я уже сплю | fail: говорит «записал 19:00» без `set_reminder` |
| зал до 22 | pass |
| давай раз в неделю | fail: спрашивает «какая практика» |
| больно, давай 40 | pass |
| квэкснутый зонд 174 | pass |

Дальше: **В1.6** (сделан). Не В2.

##### В1.6 — Живой рот пишет стол, болтовня рядом

**Зачем.** Live 3/8: модель болтает и не вызывает tools. PO: болтать можно, но запись/пропуск/час/ритм/цель в том же ходе через инструмент.

**Статус: готов** (2026-08-20). PO: болтать можно, сайд-эффект через tool. Default pytest 49/8 skip. Live **8/8**.

**Входит.** `SYSTEM_PROMPT`; один nudge в `run_turn` после первого хода без tools. Юнит на nudge с фейковым провайдером. Live-инварианты В1.5 зелёные.

**Не входит.** `tool_choice=any` / обязательный tool на каждый ход (сломает объяснение и бред). Новые имена tools. Золотые JSON. Swift. В2. Полир UI.

**Готово когда.** `pytest` в `apps/api` зелёный. `pytest -m live` — 8/8 (или skip без ключа). Scripted founding + В1.2 без регрессии. Текст ответа может быть длинным.

**Контракт (PM, 2026-08-20).** PO: болтать норм; сайд-эффект только через tool.

1. **Промпт** (`talk/spec.py`). Три пули про зал/час **оставить**. Добавить явно (смысл, не обязательно дословно):
   - Болтать можно. Сказать «записал / поставил / ужал» без вызова инструмента — баг.
   - Не уточнять **вместо** записи. Сначала tool с умолчанием, вопрос — в тексте после.
   - Умолчание субъекта: `focused_widget_id` со стола; иначе виджет на Сегодня (due / running); для повторов/цели/ритма без имени — `push-ups`.
   - «запиши зал» → `create_widget` counter сразу, **без** `set_reminder`.
   - «сегодня не сходил» → `skip` due-виджета (bike-reminder), не вешать новый час.
   - «давай раз в неделю» → `shrink_subject` или `set_cadence` week count=1 на умолчанную практику.
   - «могу N, хочу M» → `update_widget` count/target + `add_cue` do-time. Метод в тексте — ок.
2. **Nudge в `run_turn`.** Если первый `complete` без `tool_calls` — не завершать ход: дописать assistant text + одно user-сообщение (константа рядом с loop, русский, без имён вендора): смысл «если реплика меняет стол — вызови tools сейчас; болтать можно; вопрос/объяснение/бред — только текст». Второй `complete`. Если снова без tools — это финальный текст. Не крутить дальше из-за пустых tools. `MAX_ROUNDS` как есть. Не `tool_choice=required`.
3. **Юнит** `apps/api/tests/unit/test_talk_nudge.py` (фейковый провайдер, без сети):
   - ход 1 text-only → ход 2 с `add_cue` → `mutated`, два `complete`.
   - ход 1 уже с tools → второго complete нет.
   - бред «квэкснутый зонд 174» scripted: `mutated is False` после nudge.
4. Не трогать: `goldens/*.json`, Swift, RFC, archive, MCP, инварианты live (текст по-прежнему можно непустой). Не копировать `fastapi-templates`.
5. Прогон: `.venv/bin/pytest` из `apps/api`; `.venv/bin/pytest -m live` с ключом из корневого / `apps/api/.env`. Не печатать ключи. Если live не 8/8 — отчёт по репликам, не маскировать skip.

**Контракт (PM, 2026-08-20).** Eval, не продукт.

1. Маркер `live` в `apps/api/pyproject.toml`. Тесты: `apps/api/tests/live/test_live_invariants.py` (+ `conftest.py` только для live).
2. **Opt-in.** Обычный `pytest` не запускает live, даже при ключах в `.env`. Считать opt-in так: `markexpr.strip() == "live"` **или** флаг `--live`. Иначе skip `opt in: pytest -m live`. Не ставить `addopts = -m "not live"` — тогда `pytest -m live` соберёт пусто.
3. Fixture живого провайдера: `Settings` из корневого `.env` и `apps/api/.env`, **`talk_mode="live"` всегда**. Нет ключа семьи `FACIO_MODEL_NAME` → `pytest.skip`, не fail. Провайдер = `provider_for`. Ход = `run_turn` как в `test_goldens.py`. Не HTTP, не мок вендора.
4. Не сравнивать с `golden.expect.tools`, `scripted`, дословным `text`. Стол и запреты:

| реплика | инвариант |
|---|---|
| могу 4, хочу 30 подряд, как? | `mutated`; push-ups `current==4` `goal==30`; `times_per_week` не вырос (>3 нельзя); `set_reminder` нет в именах; есть do-time cue на push-ups, текст ≠ посев «держи корпус и ягодицы»; `snapshots` не пуст; `text` не пуст |
| запиши зал | `mutated`; `create_widget` type counter, `subject_id` ∉ {bike, push-ups, vegetables}; у **этого** субъекта 0 reminder; в именах нет `set_reminder`; bike `latest_by==19:00`; `bike-reminder` на месте |
| сегодня не сходил | `mutated`; есть успешный `skip`; нет `set_reminder`; bike `latest_by==19:00` |
| напомни в 19, в 21 я уже сплю | `mutated`; bike `latest_by==19:00` и **не** 18:00; в `set_reminder` нет `closes_at` 21:00; есть timing-cue на bike (в тексте «сп»); `add_cue` в именах |
| зал до 22 | `mutated`; bike `closes_at==22:00` `latest_by==19:00`; `set_reminder` с `closes_at` 22:00, без ручного `latest_by` 19:00 |
| давай раз в неделю | `mutated`; push-ups `times_per_week ≤ 1`; `goal ≤ 30` |
| больно, давай 40 | цель push-ups ≤ 30; ритм не вырос; если был `update_widget`/`set_cadence` на рост — `ok is False` / `pain_forbids_raise` |
| квэкснутый зонд 174 | `mutated is False` (live **может** вызвать `list_desk` — пустой `tool_calls` не требовать) |

5. Юнит (не `live`): helper opt-in/skip без ключа — без сети. Не печатать ключи.
6. Не трогать: `goldens/*.json`, `SYSTEM_PROMPT`, Swift, RFC, archive, MCP, `talk/loop.py` (кроме импорта, если не нужно). Не копировать `fastapi-templates`.

Провал с ключом → остановить, отчёт PM (реплика, имена tools, что на столе). Не править промпт.

---

#### Волна 2 — неделя и пауза, ещё локально

После В1. Календарь считается из ритма, не рисуется моделью. Пуш чек-ина — локальный. Закон слотов — в `packages/domain`; HTTP не остаётся одним `talk/turn`, если Inspect/клиенту нужен превью недели — отдельный роутер, без Postgres.

##### В2.1 — Развёртка слотов

**Зачем.** «Сегодня / завтра / 7 дней» без календаря-продукта и без LLM.

**Статус: готов** (2026-08-20). `slot_horizon`: 7 дней от origin + `later`. Остаток недели на границе периода не становится долгом вторника. Domain 68.

**Входит.** Чистая функция в `packages/domain`: ритм + случаи → вхождения на даты. Ритм — N раз за период, не дни недели (Q26). Тесты на фикстурах / `founding_desk`.

**Не входит.** UI. Swift. Сервер. Новые talk-имена. Пауза (В2.3). Крышка. `lid_projection` не трогать. `fastapi-templates`.

**Готово когда.** Закон отдаёт ровно 7 дней от `origin` и список дат дальше без тел слотов. `pytest packages/domain` зелёный.

**Контракт (PM, 2026-08-20).** Закон, не Inspect.

Q26: пропуск вторника — не провал. Не назначать «отжимания по вт/чт/сб».

```text
packages/domain/src/facio_domain/slots.py
packages/domain/tests/test_slots.py
```

Модели (имена можно чуть короче, смысл тот):

- `SlotKind`: `due` | `done`
- `Slot`: `subject_id`, `date`, `kind`, `instance_id: str | None` (`None` = проекция, не случай на столе)
- `DayStrip`: `date`, `slots: list[Slot]`
- `Horizon`: `days: list[DayStrip]` длина **7**; `later: list[date]` — даты **строго после** 7-го дня, где есть **реальный** instance, уникальные, по возрастанию, **без** Slot

`slot_horizon(desk: Desk, origin: date) -> Horizon`

Правила:

1. Retired (`SubjectStatus.retired`) — без проекций; реальные случаи в окне всё же показать.
2. `cadence.none` — только реальные случаи, без проекций.
3. Период: `day` = календарный день; `week` = ISO пн–вс (`date.isocalendar()` / weekday Monday=0). `window` субъекта **не** выбирает день (час — не слот).
4. В периоде: `completed_n` = случаи `InstanceStatus.completed` с `when.date()` в периоде. `open_n` = `prepared` / `in_progress` в периоде. `to_project = max(0, cadence.count - completed_n - open_n)`.
5. Реальный случай на дату: `completed` → `done` + `instance_id`; иначе `due` + `instance_id`. Не больше одного слота субъекта на дату из реальных (если два — оба, не молчать; обычно один).
6. Проекции: даты периода ∩ `[origin, origin+6]`, **без** случая этого субъекта, по возрастанию, первые `to_project`. Не класть проекцию в прошлое (`< origin`). Не переносить невместившийся остаток на следующий период как «долг вторника» — у следующей недели свой count.
7. Ежедневный `1×/day`: каждый день горизонта без completed/open — одна проекция `due`.
8. `later`: `when.date() > origin + 6 days`, любой не-retired субъект.

Тесты (`NOW.date()` для founding = **2026-08-15, суббота**):

- горизонт ровно 7 дат, первая = origin, шаг 1 день
- founding: vegetables сегодня `due` с `vegetables-open`; следующие дни горизонта — проекция vegetables `due`, `instance_id is None`
- founding: push-ups в эту ISO-неделю не помечают пн–пт до origin как пропуск; на origin есть `push-ups-open` `due`
- среда origin, стол только push-ups 3×/week без случаев: проекции на ср/чт/пт, **не** на прошедшие пн/вт
- completed во вторник при origin=среда: вторника нет в `days`; не `later`
- instance на origin+10: дата в `later`, не в `days`
- `cadence.none` без случаев: ни проекций
- `window` bike не двигает слоты на другой день

Экспорт в `facio_domain/__init__.py`. Не мокать. Не трогать: Swift, RFC, archive, `talk/`, MCP, золотые JSON рта.

##### В2.2 — Окно 7 дней на Inspect (не на крышке)

**Зачем.** Видимое окно. Крышка остаётся сегодня.

**Статус: готов** (2026-08-20). Порт `SlotLaw` 1:1. Inspect: 7 клеток + later-заголовки. InstanceStrip на месте. xcodebuild 112. Крышку не трогали.

**Входит.** Порт `slot_horizon` на Swift. Полоса 7 дней на Inspect + заголовки дат дальше. Не `TabView`. InstanceStrip и плюс остаются.

**Не входит.** Редактор расписания. Крышка-календарь. Док на Inspect. Полир шторки. В2.3. Новые talk-имена.

**Готово когда.** Inspect показывает неделю этого субъекта; крышка не сетка. `xcodebuild` test зелёный.

**Контракт (PM, 2026-08-20).** Inspect, не крышка.

Порт закона 1:1 с Python `facio_domain.slots`:

- `Facio/Domain/Law/SlotLaw.swift` — `SlotLaw.horizon(desk:origin:)`
- модели рядом (`Slot`, `SlotKind`, `DayStrip`, `Horizon`) в `Facio/Domain/Models/`
- **ISO-неделя пн–вс как Python `date.weekday()` (пн=0).** Не `Calendar.current.firstWeekday` (локаль сломает тесты и Q26).
- Тесты `FacioTests/SlotLawTests.swift`: те же случаи, что `packages/domain/tests/test_slots.py` (founding 2026-08-15 суббота; среда 3×/week без случаев → ср/чт/пт; leftover сб не долг понедельника; +10 дней → later; cadence none; bike window не двигает день).

Inspect (`InspectScreen`):

1. Считать `horizon` из `store` snapshot (subjects + instances) и `origin =` календарный день `selected.when` **или** сегодня, если выбранного нет. Проще и вернее для «окно вперёд»: **origin = начало сегодняшнего дня** (как закон), не день выбранного случая в прошлом.
2. Полоса **7 клеток** этого субъекта: дата (день месяца / короткий weekday). `due` / `done` отличимы; пусто если слота субъекта нет. Не `TabView`, не pager.
3. Тап по дню с `instance_id` → `selectedId` (как чип). Тап по проекции (`instance_id == nil`) **не** создаёт случай.
4. Ниже: `later` даты, у которых есть случай **этого** субъекта — только заголовок даты (`DisplayCopy.loudDate` или chipDate), без тела слота. Даты later без этого субъекта не показывать.
5. `InstanceStrip` + плюс как сейчас. Громкая дата выбранного случая остаётся. Дока нет. `generation` нет.

Не трогать: LidFeed / pan / dock / Use / RFC / archive / API. Не полир.

Готово: `xcodegen generate` если новые файлы; `xcodebuild -scheme Facio -destination 'platform=iOS Simulator,name=iPhone 17' test`.

##### В2.3 — Заморозка по боли + локальный чек-ин

**Зачем.** «Сегодня пропустил, спина болела» → не рост цели; офер заморозить, пока не скажет, что отпустило; через 2 дня пуш «готов тренироваться?» с устройства.

**Статус: код в git** (`672626c`, 2026-08-20). Догфуд на телефоне нашёл дыры; фикс (снимок/Use/дверь/слив правил) **в рабочем дереве, не закоммичен**. Ждём повторный прогон PO.

**Входит.** Статус паузы в законе (не `shrink` / не `retire`). Обычные напоминания практики молчат, пока пауза. Одноразовый локальный чек-ин через `ReminderScheduler`, текст шаблонный, LLM в момент выстрела нет. Золотые до новых имён (Q22): боль+пропуск → freeze, цель не 40; «отпустило» → снять паузу.

**Не входит.** APNs. RAG. «Постарайся». Крышка-календарь. Полир UI. Postgres. `fastapi-templates`. Новые talk-имена сверх `freeze_subject` / `thaw_subject`. Live-хак `addopts`.

**Готово когда.** На симуляторе реплика про спину замораживает; подставленные «+2 дня» дают локальный пуш; ответ в чате снимает паузу. Domain pytest + `apps/api` pytest (live skip) + xcodebuild test зелёные.

**Контракт (PM, 2026-08-20).** Пауза — статус практики, не карточка срыва и не shrink.

Q22: золотые `pain_skip_freeze` и `thaw_pause` **в том же диффе**, что имена. Игла `miss_skip` = «сегодня не сходил» — **не** класть её в новую реплику (`match_golden` берёт первый файл).

Закон:

```text
packages/domain/src/facio_domain/models.py      # SubjectStatus.paused; Subject.paused_at: datetime | None = None
packages/domain/src/facio_domain/subjects.py    # freeze_subject / thaw_subject + pause_check_in_at
packages/domain/src/facio_domain/tools.py       # freeze_subject, thaw_subject in TOOL_NAMES (стало 18)
packages/domain/src/facio_domain/drift.py       # paused → не срыв
packages/domain/src/facio_domain/slots.py       # paused как retired: без проекций; реальные случаи показать
packages/domain/src/facio_domain/lid.py         # виджеты paused-субъекта не на крышке (все секции)
packages/domain/tests/test_tools.py             # freeze/thaw; pain всё ещё режет raise
packages/schema/                                # python -m facio_domain.export_schema
```

Правила закона:

1. `freeze_subject(s, now)`: `status=paused`, `paused_at=now`. Цель и ритм **не** трогать. Инстансы и cue не удалять. Повторный freeze сдвигает `paused_at` (новый чек-ин +2д). Retired → `invalid`.
2. `thaw_subject(s)`: только из `paused` → `active`, `paused_at=None`. Не paused → `invalid`. Не shrink, не retire.
3. `pause_check_in_at(paused_at) = paused_at + 2 days`. Константа `PAUSE_CHECK_IN = timedelta(days=2)`. Не LLM.
4. `is_drifting`: `paused` как `retired` — False.
5. `slot_horizon`: paused без проекций (как retired).
6. `lid_projection`: виджет с `subject.status == paused` не попадает в today / lifetime / soon / postponed.
7. Tools: `freeze_subject({subject_id})`, `thaw_subject({subject_id})`. Pain **не** блокирует freeze (это не raise). Pain по-прежнему блокирует set_cadence/update target вверх.

Рот:

```text
apps/api/src/facio_api/talk/spec.py             # схемы + SYSTEM_PROMPT
apps/api/goldens/pain_skip_freeze.json
apps/api/goldens/thaw_pause.json
apps/api/tests/unit/test_goldens.py             # ids + два теста
apps/api/src/facio_api/mcp/session.py           # «16 имён» → TOOL_NAMES (длина списка)
```

Промпт (добавить, founding-буллеты не ломать):

- Боль + пропуск → `skip` due-виджета **и** `freeze_subject` этой практики. Не `update_widget` цель вверх. Не shrink/retire. Не «постарайся».
- Умолчание пропуска без имени — `bike` / `bike-reminder` (как `miss_skip`).
- «отпустило» / готов снова → `thaw_subject` той же практики (focused или единственная paused).
- Сказать «заморозил» без tool — баг.

Золотые:

- `pain_skip_freeze`: utterance **«сегодня пропустил, спина болела»**, match `["спина болела"]` (не пересекать `сегодня не сходил`). Scripted: `skip` `bike-reminder`, затем `freeze_subject` `bike`. Expect: mutated, tools `skip`+`freeze_subject`, forbidden `set_reminder` и raise, push-ups goal ≤ 30, bike `status=paused`, `paused_at` = now хода.
- `thaw_pause`: utterance **«отпустило»**, match `["отпустило"]`. Scripted: `thaw_subject` `bike`. **Стол теста — не founding as-is:** сначала `freeze_subject` bike на founding, потом `run_turn`. После: bike `active`, `paused_at is None`.

Live (опционально, `-m live`): инвариант «спина болела» → bike paused, goal push-ups не 40. Не расширять `live_play` ради thaw, если долго.

Крышка:

```text
apps/mobile-swiftui/Facio/Domain/Models/SubjectStatus.swift   # paused
apps/mobile-swiftui/Facio/Domain/Models/Subject.swift         # pausedAt
apps/mobile-swiftui/Facio/Domain/Law/SubjectLaw.swift         # freeze/thaw
apps/mobile-swiftui/Facio/Domain/Law/DriftLaw.swift           # paused → не срыв
apps/mobile-swiftui/Facio/Domain/Law/SlotLaw.swift            # paused без проекций
apps/mobile-swiftui/Facio/Domain/Law/LidProjectionLaw.swift   # скрыть виджеты paused
apps/mobile-swiftui/Facio/Domain/Law/DisplayCopy.swift        # check-in body
apps/mobile-swiftui/Facio/Store/ReminderScheduler.swift
apps/mobile-swiftui/FacioTests/ReminderSchedulerTests.swift
apps/mobile-swiftui/FacioTests/SubjectLawTests.swift          # или ModelTests + scheduler
```

Пуш:

1. `ReminderScheduler.alarms`: reminder-виджет **молчит**, если субъект `retired` **или** `paused`.
2. Для каждого `paused` с `pausedAt`: `fireAt = pausedAt + 2 days`; если `fireAt > now`, добавить будильник. Id: `reminder:check-in:{subjectId}` — префикс `reminder:` уже стирает pending в `apply`.
3. Title = `DisplayCopy.title`. Body = шаблон **«готов тренироваться?»** (`DisplayCopy.pauseCheckInBody`). Не LLM. Тап как сейчас → крышка.
4. После thaw `pausedAt` нет — чек-ин не ставится. Повторный freeze двигает час.
5. Тест: founding bike freeze at `now` → нет gym-alarm `reminder:bike-reminder` (или fire в прошлом — как сейчас), есть check-in на `now+2d`. Retired без check-in. Thaw → check-in пропал.

Не трогать: LidFeed вёрстку, pan, dock, Use, Inspect полосу (кроме того что SlotLaw сам перестанет проецировать paused), RFC сверх уже внесённых строк, archive, Postgres, APNs, `generation`.

Готово: `packages/domain/.venv/bin/pytest packages/domain`; `cd apps/api && .venv/bin/pytest`; `cd apps/mobile-swiftui && xcodegen generate && xcodebuild -scheme Facio -destination 'platform=iOS Simulator,name=iPhone 17' test`.

---

#### Волна 3 — база, облако, поиск по своим фактам

Раскрытый шаг 6. Крышка без сети всё ещё тикает.

##### В3.1 — Аккаунт и сервер записи

**Зачем.** Стенд `talk` из клина не держит счета, синк и пуш. Здесь появляется настоящий бекенд: пользователи, стол, не только ход модели.

**Входит.** Sign in with Apple (Q19, PO 2026-08-20). Крышка и рот до этого шага без логина. Postgres как правда о субъектах/виджетах/случаях/подсказках. Телефон — кэш. Два канала: структура vs прогресс. Пакеты `accounts/` и `desk/` в том же `apps/api`, отдельные роутеры, миграции, интеграционные тесты с тестовой БД. Можно опереться на `.cursor/skills/fastapi-templates/` (сессия БД, репозитории) — закон не переезжает в `item_service`, вход Apple не generic JWT users. Не копировать архивный compose слепо. Team ID как в [identity](./identity.md).

**Не входит.** Google (пока нет Android/web). Device-id как долгий вход. RAG. Идеальный мульти-девайс до бэкапа. Вынести «desk-service» в другой репозиторий/контейнер без нужды.

**Готово когда.** Холодный старт с кэша открывает Сегодня; после входа стол поднимается с сервера; `main.py` не содержит SQL и Apple-логики.

##### В3.2 — Облачный пуш

**Зачем.** Чек-ин «готов?» и час зала, когда приложение убито.

**Входит.** Device token, APNs, пакет `jobs/` (воркер или тот же процесс с отдельным входом). Тот же объект, что в В2; доставка с сервера. Текст шаблона. Не класть рассылку в `run_turn`.

**Не входит.** LLM в момент выстрела. Win-back «мы скучаем».

**Готово когда.** Пауза +2 дня доезжает пушем без открытого приложения (устройство с токеном).

##### В3.3 — Retrieval опыта, не корпус спорта

**Зачем.** «Поясница уже была» — из своих подсказок и журнала, когда `get_subject` мало.

**Входит.** Индекс фактов стола (cue + journal), tool вроде `search_facts` после золотого, модуль рядом с `desk/`, не промпт «засоси всю переписку». Не сырая переписка, не каталог упражнений.

**Не входит.** RAG «как правильно отжиматься из интернета».

**Готово когда.** Золотой: запрос про спину находит старый cue, не поднимает цель.

---

#### Что не трогаем, пока волны идут

- Принятый клин крышки/шторки, несущие костыли шага 5, посев велосипеда с 19:00.
- Док: `facioComposerDock()` только Lid/Use.
- `docs/rfc` не подгонять под волну. Если пауза или 7 дней меняют продукт сильнее закона — сначала RFC, потом код.
- Шаг 7 (измерения) — отдельно.

### 6. Сервер записи, вход, синк

Настоящие счета до синка на несколько устройств. Два канала: структура (поздняя версия) / прогресс (слияние по элементу). Не одна перезапись всего виджета.

Для TestFlight на десятки достаточно Sign in with Apple и бэкапа стола — не ждать идеальный синк, чтобы позвать людей. Google не в этой волне.

**Статус: раскрыт как волна В3.** Не начинать до акцепта плана и до В1. Облачный пуш и retrieval — части этой волны, не отдельный «RAG-проект» в В1.

### 7. Измерения

Считать: попадания подсказок, срыв за один период ритма, практики живы на четвёртой неделе, доля разговоров → механика, цена за активный день. Платный тариф не открывать, пока нет числа.

**Статус: не начинать без PO.**

---

## Критерии убийства (писать до жизни на человеке, не после)

- За две недели ни одна подсказка не была прочитана в момент дела, когда это было важно — механика не работает.
- Срыв ни разу не всплыл до того, как провал уже случился — то же.
- На записи founding journey не считывается за полторы минуты — для витрины рано, даже если закон зелёный.

Автор, потом второй человек из RFC. Если сработало — право искать чужого и звать TestFlight, не право строить сковородку «чтобы в портфолио было полно».

---

## Кто чем владеет

| Слой | Пока живём на устройстве (В1–В2) | Когда появится синк (В3) |
|------|--------------------------|---------------------|
| Схемы | питон + типы на клиенте | то же |
| Срыв, крышка, час | проверки на питоне + тонкий порт на Swift | питон — источник, клиент кэширует |
| Рантайм виджета | только телефон | только телефон |
| Разговор | удар из телефона в FastAPI | тот же сервис |
| Напоминания | системные, локально | локально; рассылка с сервера если локальных мало |
| Правда о состоянии | склад на устройстве | база; крышка читает кэш |

---

## Журнал событий (заложить в шаге 1)

Писать сразу:

- подсказку записали / показали / применили;
- случай начали / закончили;
- число счётчика, прошедшее время;
- практику уменьшили / убрали.

Попадания и поздний синк читают тот же журнал.

---

## Явно не в этой работе

Чертёжный язык, экономика намерений, биллинг тренера, соцсеть, «любая цель», клон дневника тренировок, готовка как клин, голос как первый вход, поиск по сырой переписке как память, каталог упражнений как RAG.
