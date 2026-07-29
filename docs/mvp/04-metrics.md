# 04 — Метрики

## Северная метрика MVP

### FCT — First Completion Time

Время от **первого Intent** (или от Commit — фиксируем оба) до **первого Сделано**.

Интерпретация:

| FCT | Сигнал |
|-----|--------|
| Минуты … сегодня | Продукт нащупал путь want → did |
| Завтра | Терпимо, смотреть долю |
| Дни / неделя+ | Почти наверняка провал активации |

Считать:

- медиана FCT (Intent → first Сделано)
- медиана FCT (Commit → first Сделано)
- **% same-day first Сделано** среди committed

---

## Воронка событий

Обязательные события в аналитике / таблице `events`:

| Событие | Когда |
|---------|--------|
| `intent_submitted` | отправил текст |
| `soft_start_shown` | paraphrase / soft-start |
| `draft_shown` | черновик Path |
| `plan_failed` | LLM/валидация не собрали путь |
| `refine_answered` | ответ на уточнение / пересбор |
| `back_navigated` | назад в refine loop |
| `accept_viewed` | полный Path + контракт |
| `committed` | **Принять путь** |
| `action_shown` | показан «Сегодня» |
| `action_done` | **Сделано** |
| `action_skipped` | **Пропустить** |
| `first_completion` | первое Сделано по проекту |
| `app_opened` | open (с project_id если есть) |
| `path_opened` | «Весь путь» после Commit |
| `repair_applied` | сдвиг / пересчёт |
| `project_switched` | multi-active |

В UI-аналитике и отчётах говорить «Сделано» / «Сегодня»; в коде событий допустимы `action_*`.

Хранить: raw intent, clarify turns, **llm_calls**, **state_versions**, outcome, domain, device_id.

Метрики **per project** и **per user**.

---

## KPI набор (что смотрим еженедельно)

### Активация

1. **Commit rate** = committed / intent_submitted  
2. **Refine rate** = projects with ≥1 refine / draft_shown  
3. **Generate/draft success** = draft_shown / intent_submitted  
4. **FCT** и **% same-day first Сделано** | committed  
5. **TTF-second** — доля second Сделано &lt; 48h | had first

### Удержание / исполнение

6. **D1 return** — доля committed, открывших app на следующий календарный день  
7. **D3 steps** — ≥2 «Сделано» к D3  
8. **Execution rate (D7)** — done / (done+skipped+overdue) за 7 дней у committed ≥7д назад  

### Продуктовый характер (анти-ChatGPT)

9. **Path revisit rate** — ≥1 `path_opened` после Commit  
10. **Multi-active share** — % users с ≥2 active  
11. **Chat requests** — если «Проблема?»; рост ради болтовни — red flag  
12. Qualitative — «поняло цель», «понятно почему сегодня», «вижу как готовить» vs «таски / чат»

### Обучение (demand + audit)

13. Распределение intent’ов / outcomes по доменам  
14. Топ формулировок и кластеры  
15. **Audit completeness** — % create/refine без raw llm или state_version (цель ≈ 0)

### Стоимость (вторично)

16. Токены / $ на draft/refine  
17. Токены / committed user  

На этапе MVP cost — informational, не kill-метрика. Монетизацию не проверяем.


---

## Ориентиры порогов (черновик, калибровать)

Для закрытого теста ~30–100 человек / 1–2 недели:

| Метрика | Слабо | Интересно | Сильно |
|---------|-------|-----------|--------|
| Commit rate | &lt; 20% | 20–40% | &gt; 40% |
| Same-day first Сделано \| committed | &lt; 25% | 25–50% | &gt; 50% |
| Median Commit→first Сделано | &gt; 24h | 2–24h | &lt; 2h |
| Second Сделано &lt; 48h \| had first | &lt; 20% | 20–40% | &gt; 40% |
| D1 return \| committed | &lt; 15% | 15–30% | &gt; 30% |

Пороги — гипотезы. Главное — **заранее записать**, что будем считать обнадёживающим, и не двигать после просмотра цифр без пометки.

---

## Чего не оптимизировать в MVP

- DAU ради DAU
- Число сообщений AI
- Длина / «красота» плана
- Coverage «любых» доменов в качестве стратегии
- Streak length

---

## Как собираем

Postgres: `events` + `conversation_turns` + `llm_calls` + `state_versions` с первой сборки.  
Nightly SQL / Metabase. Amplitude не обязателен.
