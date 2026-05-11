# Технологический стек CDP Generation

> Все версии — стартовые ориентиры. Перед каждой установкой / обновлением — сверить с актуальной документацией через Context7 MCP.

## Базовый стек

### Язык и runtime

- **Python 3.12** — основной язык
  - Современный синтаксис типов (`list[str]`, `dict[str, Any]`, `int | None`)
  - PEP 695 type aliases (если понадобится)

### Управление зависимостями

- **`venv`** — стандартный модуль Python для виртуальных окружений
- **`pip`** + `requirements.txt` — простой и понятный путь
- Альтернатива на потом: `uv` (быстрее), `poetry` (удобнее) — но не на старте

### Веб-интерфейс

- **Streamlit ≥ 1.40** — для фазы 1
  - Простой Python-only фреймворк, не требует JS
  - Кастомизация темы через `.streamlit/config.toml`
  - Кастомный CSS через `st.markdown(..., unsafe_allow_html=True)`
- **FastAPI + Next.js / SvelteKit** — для фазы 2 (если понадобится более сложный UI)

### LLM SDK

- **Anthropic SDK ≥ 0.40** — Claude Opus 4.7 (творческое ядро) и Claude Haiku 4.5 (дешёвый extract)
- **Anthropic-only стратегия в фазе 1** (2026-05-07): Gemini и Groq убраны из стека ради простоты. Всё, что в спеке делалось через Gemini Flash, теперь делается через Claude Haiku 4.5.
- *Если Gemini вернётся в фазу 2:* использовать новый унифицированный SDK **`google-genai`** (`from google import genai`) — пакет `google-generativeai` deprecated.

### Парсинг и HTTP

- **`httpx` ≥ 0.27** — async HTTP-клиент
- **`requests` ≥ 2.32** — sync HTTP для простых случаев
- **`beautifulsoup4` ≥ 4.12** + **`lxml` ≥ 5.3** — парсинг HTML

### Шаблонизация

- **Jinja2 ≥ 3.1** — рендеринг HTML-шаблонов из промежуточных данных

### Валидация и модели

- **Pydantic v2 ≥ 2.9** — все контракты данных, конфиги, парсеры
- **Pydantic-Settings ≥ 2.6** — отдельный пакет, начиная с v2 не входит в `pydantic` (явная зависимость в `requirements.txt`)

### PDF-рендеринг

- **headless Chrome / Edge** — встроено в Windows, генерация PDF из HTML
- Альтернатива: `weasyprint` (если headless Chrome будет проблемой на хостинге фазы 2)

### БД

- **Фаза 1: SQLite** — встроено в Python через `sqlite3`
- **Фаза 2: Supabase (Postgres)** — через `supabase-py` ≥ 2.10

### ORM / прямой SQL

- Фаза 1: прямой SQL через `sqlite3` (схема простая)
- Фаза 2: прямые операции через Supabase client + сложные миграции через Supabase MCP

### Конфигурация

- **`python-dotenv` ≥ 1.0** — `.env` для секретов
- Pydantic Settings для типизированных конфигов

### Тестирование

- **`pytest` ≥ 8.3** — основной фреймворк
- **`pytest-asyncio` ≥ 0.24** — для async-кода
- Smoke-тесты на эталонных кейсах (LW Group, Level Group)

## Фазы 2 — дополнительно

- **`supabase-py` ≥ 2.10** — клиент Supabase
- **`pyTelegramBotAPI` ≥ 4.24** или собственная HMAC-валидация — Telegram auth
- **GitHub Actions** — CI/CD
- **Streamlit Cloud / Vercel / Render** — хостинг (выбрать на этапе перехода в фазу 2)

## Внешние сервисы

| Сервис | Что использует | Стоимость |
|---|---|---|
| Anthropic Claude (Opus + Haiku) | весь pipeline — scenario-author, data-scout, doc-keeper | Платно (~160–280 ₽ на одно КП) |
| Telegram BotFather | Создание бота для auth (фаза 2) | 0 ₽ |
| GitHub | Версионирование, CI/CD | 0 ₽ (private repos для одного аккаунта) |
| Supabase | БД, Storage, Auth (фаза 2) | Free tier (500 MB DB, 1 GB Storage) |
| Streamlit Cloud / Vercel / Render | Хостинг (фаза 2) | Free tier при низком трафике |

**Итого: фаза 1 — затраты только на Anthropic API (~1.6–2.8 тыс ₽/мес).**
**Фаза 2 — добавляются 0 ₽/мес при умеренном использовании free tiers.**

## MCP-серверы (обязательны через Claude Code)

- **Context7** (`mcp__claude_ai_Context7__*`) — актуальная документация библиотек
- **Supabase** (`mcp__claude_ai_Supabase__*`) — все операции с БД (фаза 2)

См. правила использования в [`spec.md`](./spec.md).

## Что НЕ берём в стек

- ❌ Тяжёлые ORM (SQLAlchemy для одного простого проекта — overkill)
- ❌ Docker для фазы 1 (избыточная сложность для одного пользователя на одной машине)
- ❌ Kubernetes / cloud-native обвязка (не для проекта одного человека)
- ❌ Свой векторный движок (для RAG из 30 md-файлов хватит in-memory эмбеддингов)
- ❌ Тяжёлые UI-фреймворки на старте — Streamlit хватает
- ❌ Отдельный CI-сервис кроме GitHub Actions
