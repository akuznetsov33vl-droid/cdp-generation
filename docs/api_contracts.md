# Контракты API · CDP Generation

> Пока проект — Streamlit-only (фаза 1), внешний API не нужен. Контракты ниже понадобятся при переходе в фазу 2 (FastAPI / Supabase Edge Functions).

## I. Внутренние контракты pipeline (фаза 1)

Все вызовы между агентами идут через типизированные Pydantic-модели (см. [`data_model.md`](./data_model.md)). Это и есть «API» внутри одного процесса.

```python
# Сигнатуры агентов
def data_scout(req: GenerationRequest) -> SiteFacts: ...
def doc_keeper(req: GenerationRequest, facts: SiteFacts) -> tuple[BriefFacts, IndustryMap, list[CaseReference]]: ...
def scenario_author(facts: SiteFacts, brief: BriefFacts, industry: IndustryMap, count: int) -> list[Scenario]: ...
def visual_designer(result: GenerationResult) -> Path:  # путь к HTML
    ...
def reviewer(result: GenerationResult) -> ReviewVerdict: ...
def pdf_renderer(html_path: Path) -> Path:  # путь к PDF
    ...
```

## II. HTTP API (фаза 2, FastAPI)

База: `https://cdp-gen.<domain>/api/v1`

### Auth

#### `POST /auth/telegram`
Принимает payload Telegram Login Widget, валидирует HMAC, выдаёт сессионный JWT.

```http
POST /api/v1/auth/telegram
Content-Type: application/json

{
  "id": 123456789,
  "first_name": "Менеджер",
  "username": "manager_username",
  "photo_url": "...",
  "auth_date": 1714838400,
  "hash": "abc123..."
}
```

```http
200 OK
Set-Cookie: session=<jwt>; HttpOnly; Secure; SameSite=Lax; Max-Age=86400

{
  "user": { "id": "uuid", "telegram_id": 123456789, "role": "manager" }
}
```

```http
403 Forbidden
{ "error": "telegram_id_not_in_allowlist" }
```

#### `POST /auth/logout`
Удаляет сессию.

#### `GET /auth/me`
Возвращает текущего пользователя.

### Clients

#### `GET /clients`
Список клиентов пользователя.

#### `POST /clients`
Создание карточки клиента.
```json
{
  "display_name": "Level Group",
  "primary_domain": "https://level.ru",
  "additional_domains": ["https://business.level.ru"],
  "industry": "real_estate"
}
```

#### `GET /clients/{client_id}`, `PATCH`, `DELETE`
Стандартный CRUD.

### Generation

#### `POST /generations`
Запускает pipeline. Асинхронная операция — возвращает `request_id`, статус узнаётся через polling или WebSocket (опционально).

```json
{
  "client_id": "uuid",
  "brief_text": "...",
  "extra_notes": null,
  "target_scenarios_count": 5
}
```

```http
202 Accepted
{
  "request_id": "uuid",
  "status": "pending",
  "estimated_seconds": 300
}
```

#### `GET /generations/{request_id}`
Текущий статус и результат (если готов).

```json
{
  "request_id": "uuid",
  "status": "completed",
  "result": { /* GenerationResult */ },
  "html_url": "https://...signed_url",
  "pdf_url": "https://...signed_url",
  "expires_at": "2026-05-08T12:00:00Z"
}
```

Возможные статусы: `pending`, `running`, `completed`, `failed`.

#### `GET /generations` — история
Параметры: `client_id`, `limit`, `offset`.

### Health

#### `GET /healthz`
Легковесный health check (БД, очередь, LLM API доступны).

## III. Стандартизация ошибок

```json
{
  "error": "machine_readable_code",
  "message": "Человекочитаемое объяснение",
  "details": { /* опционально, контекст */ }
}
```

Коды:
- `unauthorized` (401)
- `forbidden_telegram_id_not_allowed` (403)
- `client_not_found` (404)
- `validation_error` (422)
- `generation_failed` (500)
- `external_api_quota_exceeded` (502)
- `internal_error` (500)

## IV. Безопасность

- **CORS:** allow-list доменов фронтенда, никаких `*` в production
- **Rate limiting:** 10 запросов/минута на эндпоинт `POST /generations` (защита от случайного перерасхода API-бюджета)
- **CSRF:** через `SameSite=Lax` cookie + явная проверка для не-GET
- **Токены:** session-cookie с `HttpOnly`; никаких токенов в localStorage
- **Логирование:** запрос/ответ без брифов и контента сценариев (PII), только метаданные
