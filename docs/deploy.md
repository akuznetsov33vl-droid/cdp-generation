# Deploy на Streamlit Cloud — пошагово

Цель: дать ссылку начальнику, чтобы он зашёл в браузере, ввёл пароль и пользовался без установки чего-либо.

## Что мы используем

- **GitHub** — хранение кода. Репозиторий `cdp-generation`, public (нужно для Streamlit Community Cloud)
- **Streamlit Community Cloud** — хостинг (бесплатно, native для Streamlit-приложений)
- **Anthropic API** — те же ключи, что и локально, передаются через Streamlit Secrets
- **WeasyPrint** — PDF-рендер на сервере (Chrome там нет)
- **Password gate** — простой пароль через `st.secrets["app_password"]`

## Шаг 1. Защитить бюджет (5 минут, сделать ДО деплоя)

1. Открыть https://console.anthropic.com/settings/limits
2. Поставить **Monthly spend limit** — рекомендую $20 для старта
3. Поставить email-нотификации на 50% и 90%

Это страховка: даже если пароль утечёт, больше $20/мес никто не потратит.

## Шаг 2. Запушить код на GitHub (10 минут)

Из корня проекта:

```powershell
git init
git add .
git commit -m "init: working MVP for cloud deploy"
gh auth login                              # один раз, github.com → https → web browser
gh repo create cdp-generation --public --source=. --push --description "AI-инструмент для индивидуальных КП Calltouch CDP"
```

После этого код будет на `https://github.com/<твой_username>/cdp-generation`.

## Шаг 3. Подключить Streamlit Cloud (5 минут)

1. Открыть https://share.streamlit.io → **Sign in with GitHub** (тем же аккаунтом)
2. **New app** → выбрать репозиторий `cdp-generation`
3. **Branch:** `main`
4. **Main file path:** `src/app.py`
5. **App URL** — можно оставить дефолт `cdp-generation-<username>.streamlit.app`
6. **Advanced settings → Secrets** — вставить содержимое `.streamlit/secrets.toml.example` и подставить реальные значения (см. ниже)
7. **Deploy**

Через 3–5 минут приложение поднимется по выданному URL.

## Шаг 4. Заполнить Secrets

В Streamlit Cloud UI: `App → Settings → Secrets`. Вставить:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."           # твой ключ из console.anthropic.com
ANTHROPIC_MODEL_OPUS = "claude-opus-4-7"
ANTHROPIC_MODEL_HAIKU = "claude-haiku-4-5-20251001"
KNOWLEDGE_BASE_PATH = "./knowledge_base/data"
OUTPUT_DIR = "./output"
SQLITE_PATH = "./data/local.db"

app_password = "Calltouch2026!"                  # пароль для входа
```

Сохранить → Streamlit перезагрузит приложение автоматически.

## Шаг 5. Отдать ссылку начальнику

URL формата: `https://cdp-generation-<username>.streamlit.app`

Начальнику в одном сообщении:

> Привет! Инструмент для генерации КП по CDP Calltouch:
> 1. Открой: <ссылка>
> 2. Введи пароль: `Calltouch2026!`
> 3. URL клиента + бриф встречи → «Сгенерировать»
> 4. Через 2–4 минуты скачаешь HTML и PDF.

## Обновления после первого деплоя

Любой `git push` в `main` → Streamlit Cloud автоматически передеплоит за ~1 минуту.

```powershell
git add .
git commit -m "fix: <что починил>"
git push
```

## Если что-то сломалось

- **App доступен, но «Authentication error»** → ANTHROPIC_API_KEY невалидный в Secrets
- **«PDF не создан»** → проверь `packages.txt` (libpango, libharfbuzz, libfontconfig, libcairo2) — для Streamlit Cloud это обязательно
- **«Папка базы знаний не найдена»** → KNOWLEDGE_BASE_PATH в Secrets должен быть `./knowledge_base/data`
- **Stuck на старте** → Streamlit Cloud → Manage app → Reboot

## Стоимость

- GitHub public repo: **0 ₽**
- Streamlit Cloud Community: **0 ₽**
- Anthropic API: **~160–280 ₽ за одно КП**, лимит $20/мес (≈1 800 ₽) защищает от перерасхода

Итого: расход равен только реально потраченному на Anthropic.
