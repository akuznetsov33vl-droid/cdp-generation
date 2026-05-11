# Спецификация CDP Generation

> Этот файл — техническая спецификация и обязательные правила работы. Любое отклонение требует явного согласия пользователя.

## 1. Назначение

Сгенерировать индивидуальное коммерческое предложение по продуктам Calltouch CDP под конкретного клиента, с уникальными сценариями под архитектуру его сайта, бизнеса и CRM.

## 2. Обязательные правила интеграций (НЕЛЬЗЯ нарушать)

### 2.1 Context7 — единственный источник актуальной документации

**Правило:** перед использованием любой внешней библиотеки, SDK, API или CLI обращаться в Context7 MCP за актуальной документацией.

**Инструменты:**
- `mcp__claude_ai_Context7__resolve-library-id` — найти идентификатор библиотеки
- `mcp__claude_ai_Context7__query-docs` — получить актуальную документацию

**Что покрывает:**
- Anthropic SDK (Claude Opus, Sonnet, Haiku)
- Google Generative AI (Gemini Flash)
- Groq (Llama 3.3)
- Streamlit, FastAPI
- Supabase (supabase-py, supabase-js, RLS, миграции)
- Telegram Login Widget, Telegram Bot API
- Pydantic v2, Jinja2, BeautifulSoup
- GitHub Actions, Vercel, Render, Streamlit Cloud
- Любые другие SDK / API / CLI

**Запрещено:** писать код по памяти, не сверившись с актуальной документацией. Версии библиотек меняются — память разработчика устаревает быстрее, чем Context7.

**Ответственный субагент:** `doc-keeper`. Любой другой субагент перед написанием кода с зависимостью обязан передать управление в `doc-keeper`.

### 2.2 Supabase — только через Supabase MCP

**Правило:** все операции с базой данных выполняются через MCP-инструменты Supabase. Никаких прямых SQL-команд из кода в обход MCP без явного указания пользователя.

**Инструменты:**
- `mcp__claude_ai_Supabase__list_projects` — выбрать проект
- `mcp__claude_ai_Supabase__list_tables` — посмотреть схему перед миграцией
- `mcp__claude_ai_Supabase__apply_migration` — применить миграцию
- `mcp__claude_ai_Supabase__execute_sql` — разовый SQL (debug, проверка)
- `mcp__claude_ai_Supabase__get_advisors` — security + performance аудит после миграции
- `mcp__claude_ai_Supabase__generate_typescript_types` — типы для frontend
- `mcp__claude_ai_Supabase__get_logs` — логи проекта при дебаге
- `mcp__claude_ai_Supabase__create_branch` — dev-ветки БД (как git, но для БД)

**Обязательная процедура для миграций:**
1. `list_tables` — узнать текущую схему
2. Написать миграцию (включая RLS-политики)
3. `apply_migration` — применить
4. `get_advisors` — проверить на ошибки безопасности и производительности
5. `generate_typescript_types` — обновить типы для клиента (если нужны)

**Ответственный субагент:** `db-architect`.

### 2.3 GitHub — деплой и версионирование

**Правило:** код живёт в GitHub-репозитории. Все изменения через коммиты в feature-ветки, мерж в `main` через Pull Request.

**Инструменты:**
- `git` CLI — локальная работа
- `gh` CLI — работа с PR, issues, releases, GitHub Actions

**Запрещено:**
- Force-push в `main`
- Прямые коммиты в `main` без PR
- Использование `--no-verify` без явного указания пользователя
- Коммиты с потенциальными секретами (`.env`, ключи, токены)

**CI/CD:**
- Push в feature-ветку → запуск тестов через GitHub Actions
- Мерж в `main` → автодеплой на хостинг (фаза 2)

**Ответственный субагент:** `deploy-engineer`.

## 3. Контракты входа и выхода

### Вход

```python
class GenerationRequest(BaseModel):
    client_url: HttpUrl                # Главный URL клиента (level.ru, brus-lw.ru)
    additional_urls: list[HttpUrl] = []# Дополнительные домены (business.level.ru, srub-lw.ru)
    brief: str                          # Свободный текст: транскрипт встречи / бриф / задачи
    extra_notes: str | None = None      # Доп. пожелания менеджера
    industry_hint: str | None = None    # Опциональная подсказка отрасли
    target_scenarios_count: int = 5     # Сколько сценариев генерировать (по умолчанию 5)
```

### Выход

```python
class GenerationResult(BaseModel):
    request_id: UUID
    client_name: str                    # Распознанное название
    industry: str                       # Распознанная отрасль
    target_segments: list[Segment]      # Сегменты ЦА
    scenarios: list[Scenario]           # Сгенерированные сценарии
    cases: list[CaseReference]          # Подобранные кейсы
    pricing: PricingBlock               # Состав решения и цены
    html_path: Path                     # Путь к HTML
    pdf_path: Path                      # Путь к PDF
    review_passed: bool                 # Прошло ли финальное ревью
    review_issues: list[str]            # Если не прошло — список замечаний
    generated_at: datetime
```

Полные модели — в [`data_model.md`](./data_model.md).

## 4. Pipeline генерации (последовательность)

```
[вход] → data-scout → doc-keeper → scenario-author → visual-designer → reviewer → PDF-renderer → [выход]
```

Подробное описание каждого этапа — в [`.claude/agents/<name>.md`](../.claude/agents/).

## 5. LLM-стратегия (Anthropic-only, single-provider)

> **Решение от 2026-05-07 (фаза 1 MVP).** Изначально предполагался гибрид Gemini Flash + Claude Opus, но в фазе 1 решили обойтись одним провайдером. Меньше ключей в `.env`, меньше точек отказа, меньше асинхронности в pipeline. Если в фазе 2 затраты по Anthropic вырастут — вернёмся к гибриду; интерфейс `src/llm.py` для этого подготовлен.

| Шаг | Модель | Стоимость | Почему |
|---|---|---|---|
| Парсинг сайта (HTML → SiteFacts) | **Claude Haiku 4.5** | ~5–15 ₽ | Структурный extract, дешёвая модель достаточна |
| Разбор брифа (BriefFacts) | Claude Haiku 4.5 | ~3–8 ₽ | То же |
| Подбор кейсов / отраслевой карты | (без LLM) | 0 ₽ | Простой keyword-RAG поверх локальных md-файлов |
| **Генерация сценариев** | **Claude Opus 4.7** | ~150–250 ₽ | Творческий, нюансированный текст |
| HTML-сборка | (без LLM) | 0 ₽ | Jinja2-шаблон — детерминированно и быстрее |
| Финальное ревью | (без LLM) | 0 ₽ | Детерминированные правила в `src/agents/reviewer.py` |

**Итоговая стоимость одного КП:** ~160–280 ₽. На потоке 10 КП/мес ≈ 1 600–2 800 ₽.

> Если в будущем Gemini вернётся в стек — использовать **новый унифицированный SDK** `google-genai` (пакет `from google import genai`), а **не** старый `google-generativeai` (deprecated). Найдено через Context7 на 2026-05-07.

> **`temperature` параметр.** Для extended-thinking-моделей (Opus 4.7) Anthropic API возвращает `400 invalid_request_error: temperature is deprecated for this model.` Поэтому в `src/llm.py` параметр опционален и по умолчанию **не передаётся** в API — модель использует свои дефолты. Если когда-нибудь понадобится управлять sampling — передавать только для не-thinking моделей. Зафиксировано 2026-05-08.

## 6. Бизнес-правила, прошитые в систему

Этот список загружается в reviewer-агента и валидируется на финальной стадии:

1. **Цены:**
   - CDP Calltouch: всегда «от 10 500 ₽/мес»
   - Big Data партнёров: всегда «от 5 000 ₽/мес»
   - Скоринг и триггер «Выявлен интерес» — включены в базовый CDP, без отдельной строки

2. **WABA / WhatsApp Business:** не вставлять в КП по своей инициативе. Только если в брифе менеджер явно указал.

3. **Конкуренты:** не упоминать в КП по своей инициативе. Имена Mindbox, Altcraft, enKod, Sendsay, Carrotquest, Roistat, Rees46 не появляются в выходном документе. Если клиент сам указал в брифе на сравнение — допустимо.

4. **Запрещённые категории отраслей** (требуют ручной обработки, инструмент должен пометить на ревью):
   - Лекарства по рецепту, прерывание беременности, БАДы (некоторые), табак, оккультные/ритуальные услуги, детская реклама, политический PR — см. [`../cdp_calltouch_kb/03_clients/03_restrictions.md`](../knowledge_base/)

5. **Реализуемость сценариев:**
   - Триггеры — только из реального списка Calltouch (11 типов)
   - Действия — только из реального списка (9 типов)
   - Минимальный объём аудитории — 500 контактов для рассылок
   - Один клиент = одна цепочка
   - Ограничения медицины (не предполагать заболевание)

6. **Smart SMS Билайн:** продажа приостановлена — не предлагать как канал.

## 7. Безопасность

- Все секреты — в `.env`, никогда в коде и не коммитятся в репозиторий
- API-ключи в `.env.example` — только как заглушки `sk-ant-api03-...`
- Перед коммитом — проверка `git diff` на наличие секретов
- При работе через Supabase MCP — всегда RLS-политики для пользовательских таблиц

## 8. Тестирование

- `pytest` — юнит-тесты для парсеров, валидаторов, моделей
- Smoke-test pipeline на двух эталонных кейсах: LW Group и Level Group (выходы лежат в `../cdp_calltouch_kb/output_lw_group/` и `output_level_group/`)
- Сравнение нового сгенерированного КП с эталонным — структурное (наличие секций, валидность цен, отсутствие конкурентов)
