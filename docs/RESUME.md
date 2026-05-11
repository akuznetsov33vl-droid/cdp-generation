# Resume · CDP Generation

> Сводный документ. Тут — всё, что нужно знать, чтобы продолжить работу с проектом, даже если забыл, что было раньше.
> Дата создания: **2026-05-08**.

---

## 🎯 Что это

AI-инструмент для генерации индивидуальных коммерческих предложений по продуктам **Calltouch CDP** под конкретных клиентов. Менеджер вводит URL клиента + бриф встречи — получает PDF со сценариями за 2–4 минуты.

---

## 🌐 Боевые ссылки

| Что | Где |
|---|---|
| **Production app** | https://cdp-generation-akuznetsov.streamlit.app |
| **Пароль входа** | `Calltouch2026!` (хранится в Streamlit Cloud Secrets как `app_password`) |
| **GitHub repo** | https://github.com/akuznetsov33vl-droid/cdp-generation (public) |
| **Streamlit Cloud Manage** | https://share.streamlit.io → app `cdp-generation` |
| **Anthropic Console** | https://console.anthropic.com (биллинг, ключи, лимиты) |

---

## 🏗️ Архитектура (как работает)

```
URL клиента + Бриф
       ↓
[1] data-scout (Haiku 4.5)       — краулит сайт (httpx + BeautifulSoup), достаёт SiteFacts
[2] doc-keeper (Haiku 4.5 + RAG) — разбирает бриф в BriefFacts, подбирает кейсы из knowledge_base/data/
[3] scenario-author (Opus 4.7)   — генерит уникальные сценарии под архитектуру Calltouch
[4] reviewer (без LLM)           — детерминированно проверяет правила (конкуренты, цены, триггеры/действия)
[5] visual-designer (Jinja2)     — собирает HTML из templates/proposal.html.j2
[6] pdf_renderer                 — WeasyPrint (cloud) → headless Chrome (локально, fallback)
       ↓
output/{client}_CDP_Proposal.{html,pdf}
```

Стоимость одного КП: **~160–280 ₽** (Opus 4.7 на сценариях + Haiku 4.5 на парсинге).

---

## 📁 Структура репо

```
cdp-generation/
├── src/
│   ├── app.py                 # Streamlit UI + password gate + st.secrets→env bridge
│   ├── orchestrator.py        # Связывает агентов в пайплайн
│   ├── config.py              # AppSettings (Pydantic) + detect_browser()
│   ├── models.py              # Все Pydantic-контракты, Literal-типы для Trigger/Action
│   ├── llm.py                 # Anthropic SDK обёртка, retry, JSON-парсинг через Pydantic
│   ├── exceptions.py          # CDPGenerationError-иерархия
│   ├── prompts.py             # Загрузчик промптов с кэшем
│   └── agents/
│       ├── data_scout.py
│       ├── doc_keeper.py
│       ├── scenario_author.py
│       ├── reviewer.py
│       ├── visual_designer.py
│       └── pdf_renderer.py
├── prompts/
│   ├── data_scout_extract.md
│   ├── doc_keeper_brief.md
│   └── scenario_author.md
├── templates/
│   └── proposal.html.j2       # Брендированный шаблон A4 + counter(page)
├── knowledge_base/
│   ├── README.md
│   └── data/                  # Snapshot базы знаний (680 КБ) — для cloud
│       ├── 01_product/  02_sales/  03_clients/  04_templates/  05_cases/
│       └── output_lw_group/  output_level_group/   (эталонные HTML)
├── tests/                     # 13 тестов, все зелёные (pytest)
├── docs/                      # spec, architecture, deploy, rules, data_model, …
├── .streamlit/
│   ├── config.toml            # Тема (фиолет + cyan)
│   └── secrets.toml.example   # Шаблон для cloud
├── packages.txt               # Системные libs для WeasyPrint (libpango, libharfbuzz, ...)
├── requirements.txt
├── pyproject.toml
├── .env.example               # Шаблон для локали (заглушки)
├── .gitignore                 # .env + secrets.toml исключены
└── CLAUDE.md                  # Инструкции для AI-ассистента (контекст проекта)
```

---

## 🔐 Секреты — где живут

### Локально (твоя машина)
Файл `.env` в корне (в git **не** коммитится):
```
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL_OPUS=claude-opus-4-7
ANTHROPIC_MODEL_HAIKU=claude-haiku-4-5-20251001
KNOWLEDGE_BASE_PATH=../cdp_calltouch_kb
OUTPUT_DIR=./output
CHROME_PATH=
SQLITE_PATH=./data/local.db
```

### В облаке (Streamlit Cloud)
`https://share.streamlit.io → app → Settings → Secrets` (TOML-формат):
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
ANTHROPIC_MODEL_OPUS = "claude-opus-4-7"
ANTHROPIC_MODEL_HAIKU = "claude-haiku-4-5-20251001"
KNOWLEDGE_BASE_PATH = "./knowledge_base/data"
OUTPUT_DIR = "./output"
SQLITE_PATH = "./data/local.db"
app_password = "Calltouch2026!"
```

---

## 🧠 Ключевые архитектурные решения

| Дата | Решение | Почему |
|---|---|---|
| 2026-05-07 | **Anthropic-only пайплайн** (Opus 4.7 + Haiku 4.5) вместо гибрида с Gemini | Один ключ, проще setup, экономия на гибриде ничтожна для одного юзера |
| 2026-05-07 | **Jinja2 + детерминированный reviewer** вместо LLM-ревью | Стабильнее, дешевле, тестируется |
| 2026-05-08 | **WeasyPrint primary, Chrome fallback** | На Streamlit Cloud нет Chrome; локально — может работать любой |
| 2026-05-08 | **Public GitHub repo + Streamlit Community Cloud** | Free tier для phase 2, частный hosting обсудим если станет нужно |
| 2026-05-08 | **Password gate (один общий пароль)** вместо Telegram Login Widget | Простой первый деплой; Telegram оставлен на фазу 2.1 |
| 2026-05-08 | **st.secrets → os.environ bridge в app.py** | pydantic-settings не читает Streamlit secrets автоматически |

---

## 🔧 Гочи и подводные камни

### Anthropic API

- **`temperature` параметр deprecated для Opus 4.7** (extended-thinking) → API возвращает 400. В `src/llm.py` параметр опционален и **не передаётся** по умолчанию
- **Модели**: `claude-opus-4-7`, `claude-haiku-4-5-20251001`
- **Spend limit** обязателен — поставь $5–20 в https://console.anthropic.com/settings/limits, без него ссылка = открытый кошелёк

### Pydantic v2 + Streamlit Cloud

- `pydantic-settings` читает env-переменные и `.env`, **НЕ** читает `st.secrets`
- В `src/app.py` есть `_hydrate_env_from_secrets()` который копирует все строки из `st.secrets` в `os.environ` **до** `get_settings()`

### Windows-окружение пользователя

- Python был только Store-stub изначально; пользователь поставил 3.14.4 (winget)
- venv в `.venv/`, не системный Python
- Если запускать локально — нужен Chrome для PDF (или установить GTK3 runtime для WeasyPrint)
- Имена файлов с кириллицей → транслитерация в `src/agents/visual_designer.py` (`_CYR_TO_LAT`)

### Знания (`knowledge_base/`)

- **Источник истины**: `../cdp_calltouch_kb/` (живая база знаний рядом с проектом)
- **Snapshot в репо**: `knowledge_base/data/` (вшит для cloud, обновлять руками)
- Локально config указывает на `../cdp_calltouch_kb/`, в облаке — на `./knowledge_base/data/`

### Google Gemini SDK (если когда-то понадобится)

- Старый `google-generativeai` **deprecated**
- Использовать `google-genai` (`from google import genai`)
- Поддерживает Pydantic-схему как `response_schema` напрямую

---

## 🚀 Как продолжать работу

### Локальный запуск

```powershell
cd "c:\Users\Mechrevo\Desktop\AI\Обучение\CDP Generation"
.\.venv\Scripts\streamlit.exe run src\app.py
```
→ http://localhost:8501

### Изменения и деплой

```powershell
# редактируешь файлы
git add .
git commit -m "fix: <что>"
git push
```
→ Streamlit Cloud автоматически передеплоит за ~1 минуту.

### Сменить пароль

Streamlit Cloud → Manage app → Settings → Secrets → меняй `app_password = "..."` → Save → автоперезагрузка.

### Поменять промпт / шаблон

Файлы в `prompts/` и `templates/proposal.html.j2`. После правки — push.

### Обновить базу знаний

Источник: `../cdp_calltouch_kb/`. После обновления:
```powershell
# скопировать актуальный snapshot в knowledge_base/data/
# (есть однострочник в логах сессии 2026-05-08, или можно написать build_kb.py)
git add knowledge_base/data && git commit -m "kb: refresh snapshot" && git push
```

### Тесты

```powershell
.\.venv\Scripts\python.exe -m pytest
```
13/13 должны быть зелёные.

---

## 📊 Финансовая модель

| Статья | Цена |
|---|---|
| GitHub public repo | 0 ₽ |
| Streamlit Cloud Community | 0 ₽ |
| Anthropic API (Opus + Haiku) | ~160–280 ₽ за одно КП |
| **Итого при потоке 10 КП/мес** | **~1 600–2 800 ₽/мес** |

Spend limit Anthropic = страховочный потолок.

---

## 🛣️ Roadmap (если захочется развивать)

### Phase 2.1 — Telegram auth
Заменить общий пароль на Telegram Login Widget + allow-list ID. Готовая дока: `docs/auth_telegram.md`.

### Phase 2.2 — История КП
Сейчас результаты только скачиваются. История в Supabase: `docs/data_model.md` уже описана схема таблиц + RLS.

### Phase 2.3 — Multi-user
Если отдел продаж захочет — добавить регистрацию по Telegram ID, разделение клиентов по `owner_user_id`.

---

## 🆘 Если что-то сломалось

1. **App не открывается**: https://share.streamlit.io → Manage app → правая панель «Logs». Скриншот логов → починим.
2. **Authentication error на Anthropic**: ключ в Secrets битый/закончились кредиты. Console → Billing.
3. **PDF не создаётся в облаке**: проверь `packages.txt` (libpango, libharfbuzz, libfontconfig, libcairo2) — должен быть закоммичен.
4. **Просто странно**: Manage app → правое верх «Reboot». Streamlit пересоберёт окружение с нуля.

---

## 📎 Связанные документы в репо

- [`docs/spec.md`](spec.md) — полная техспека и обязательные правила
- [`docs/deploy.md`](deploy.md) — пошаговая инструкция деплоя (для повторного использования)
- [`docs/architecture.md`](architecture.md) — двухфазная архитектура
- [`docs/visual_identity.md`](visual_identity.md) — палитра, шрифты, бренд
- [`docs/rules.md`](rules.md) — правила работы (Git, безопасность, тестирование)
- [`docs/data_model.md`](data_model.md) — Pydantic-модели + Supabase-схема для фазы 2
- [`CLAUDE.md`](../CLAUDE.md) — инструкции для AI-ассистента в будущих сессиях
- [`Project_IDEA.md`](../Project_IDEA.md) — развёрнутая концепция

---

## ✅ Чек-лист «всё в порядке»

- [x] MVP работает локально (генерация level.ru → HTML+PDF за 2.5 минуты)
- [x] Тесты 13/13 зелёные
- [x] GitHub repo `akuznetsov33vl-droid/cdp-generation` (public)
- [x] Streamlit Cloud задеплоен, password gate работает
- [x] Secrets настроены, `ANTHROPIC_API_KEY` читается
- [x] KB-snapshot вшит в репо
- [x] WeasyPrint в `requirements.txt` + `packages.txt`
- [ ] **Spend limit $5–20 в Anthropic Console** ← остаётся сделать вручную
- [ ] Первая боевая генерация на облаке (проверка end-to-end на cloud)
