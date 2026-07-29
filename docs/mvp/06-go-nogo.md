# 06 — Критерии go / no-go

Решение после закрытого теста (рекомендуется: **≥30 committed пользователей** или **2 недели** — что наступит раньше при активном наборе).

---

## Go (инвестируем в RFC-глубину: blueprints, wedge, repair library)

Все базовые условия:

1. Same-day first Сделано ≥ **~30%** committed (или медиана Commit→Сделано &lt; **12h**)  
2. Среди тех, у кого было first Сделано: second &lt; 48h ≥ **~25%**  
3. D1 return ≥ **~20%** committed  
4. Качественно: «поняло цель» + «понятно почему сегодня» + path-heavy «вижу маршрут/как готовить»; не «только поболтали»  
5. Audit trail полный (create/refine без raw llm/state ≈ 0)  
6. Нет критичного safety-инцидента  

Тогда: wedge по demand, blueprints из логов, deterministic repair.

---

## Iterate (не хоронить, не масштабировать архитектуру)

Сигналы смешанные, например:

- Commit низкий → слабый draft/paraphrase или Path страшный → улучшить soft-start + detail  
- Refine высокий, Accept низкий → вопросы бесят / пересбор ломает путь  
- Path без how-to в готовке → `detail` + prompt  
- Multi-active роняет execution → soft focus  
- FCT ок, D1 мёртвый → reminders / качество 2-го «Сегодня»  

Порог: ещё **один** короткий цикл эксперимента, не VectorDB.

---

## No-go (гипотеза Facio-as-execution не подтверждена этим UX)

Любое из:

1. Same-day first Сделано &lt; **~15%** при нормальном draft success  
2. Почти никто не делает второй шаг  
3. Хотят только чат/советы, игнорируют «Сделано»  
4. Не стабилизируется валидный Execution State / пустые `why` массово  

Тогда: либо смена гипотезы (узкий wedge-only без «любое хочу»), либо пауза — **не** лечить отсутствие return через Intent Economy / marketplace.

---

## Что сказать команде на review

Один слайд:

- FCT / same-day first Сделано  
- Second &lt; 48h  
- D1 return  
- Refine rate + Commit rate  
- Multi-active share  
- Топ доменов + audit completeness  
- Вердикт: Go / Iterate / No-go + следующий эксперимент одной строкой  

Архитектурные RFC открывать широко только на **Go** (или узкий tech-debt на Iterate).
