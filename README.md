# CDP Generation

> AI-инструмент для автоматической генерации индивидуальных коммерческих предложений по продуктам Calltouch CDP под конкретных клиентов.

## 🌐 Production

**App:** https://cdp-generation-akuznetsov.streamlit.app
**Пароль:** см. Streamlit Cloud Secrets (`app_password`)

**Полное описание состояния, архитектуры и гочей:** [`docs/RESUME.md`](./docs/RESUME.md)

## Быстрый старт (фаза 1, локально)

```bash
# 1. Установить Python 3.12 (https://www.python.org/downloads/)

# 2. Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 3. Поставить зависимости
pip install -r requirements.txt

# 4. Скопировать шаблон env и заполнить ключи
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux

# 5. Запустить веб-интерфейс
streamlit run src/app.py
```

## Документация

- [`idea.md`](./idea.md) — идея проекта в одну страницу
- [`Project_IDEA.md`](./Project_IDEA.md) — развёрнутая концепция
- [`CLAUDE.md`](./CLAUDE.md) — инструкции для Claude Code (правила работы в проекте)
- [`docs/spec.md`](./docs/spec.md) — спецификация и обязательные правила интеграции
- [`docs/architecture.md`](./docs/architecture.md) — двухфазная архитектура
- [`docs/visual_identity.md`](./docs/visual_identity.md) — брендинг
- [`docs/auth_telegram.md`](./docs/auth_telegram.md) — авторизация по Telegram (фаза 2)
- [`docs/stack.md`](./docs/stack.md) — технологический стек
- [`docs/rules.md`](./docs/rules.md) — правила и законы проекта
- [`docs/data_model.md`](./docs/data_model.md) — модель данных
- [`docs/api_contracts.md`](./docs/api_contracts.md) — контракты API
- [`.claude/agents/`](./.claude/agents/) — спецификации специализированных субагентов
- [`knowledge_base/README.md`](./knowledge_base/README.md) — связь с базой знаний CDP Calltouch

## Текущая фаза

🟢 **Фаза 1 — локальная разработка**. Цель: рабочий MVP на машине разработчика, минимум 5 реальных КП, сгенерированных инструментом.

После фазы 1 → перенос в личное облако, Supabase, Telegram-авторизация, GitHub-деплой (фаза 2).

## Стек

Python 3.12 · Streamlit · Anthropic SDK (Claude Opus 4.7 + Haiku 4.5, single-provider) · Jinja2 для HTML · headless Chrome/Edge для PDF · SQLite (фаза 1) → Supabase (фаза 2)

> Изменено относительно изначального плана (2026-05-07): фаза 1 идёт на одном провайдере (Anthropic). Gemini/Groq убраны для простоты setup'a — описано в `docs/spec.md`, раздел 5.

## Лицензия

Приватный проект для одного пользователя. Никакого распространения без явного согласия владельца.
