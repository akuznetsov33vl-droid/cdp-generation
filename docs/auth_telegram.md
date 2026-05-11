# Авторизация по Telegram ID

> Этот документ относится к фазе 2 — облачной версии. В фазе 1 (локальной) авторизация не нужна, доступ ограничен физическим доступом к машине.

## Зачем именно Telegram

- Уже работает у пользователя (он в Telegram)
- Не нужны пароли — авторизация по подписи виджета
- Allow-list по `telegram_id` исключает посторонних, даже если URL попадёт наружу
- Нет работы с почтовыми сервисами, SMS-провайдерами, OAuth-провайдерами

## Архитектура

```
┌──────────────────────────────────────────────────────────────┐
│  Браузер пользователя                                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Telegram Login Widget                                  │  │
│  │ <script src="https://telegram.org/js/                  │  │
│  │   telegram-widget.js?22"                               │  │
│  │   data-telegram-login="<bot_username>"                 │  │
│  │   data-size="large"                                    │  │
│  │   data-onauth="onTelegramAuth(user)">                  │  │
│  │ </script>                                              │  │
│  └─────────────────┬──────────────────────────────────────┘  │
└────────────────────┼─────────────────────────────────────────┘
                     │ user object: id, first_name, username,
                     │ photo_url, auth_date, hash
                     ▼
┌──────────────────────────────────────────────────────────────┐
│  Сервер (FastAPI / Streamlit)                                │
│                                                              │
│  1. Принимает payload                                        │
│  2. Проверяет HMAC-подпись на TELEGRAM_BOT_TOKEN             │
│     (валидация по официальному алгоритму Telegram)           │
│  3. Проверяет user.id ∈ ALLOWED_TELEGRAM_IDS                 │
│  4. Если всё ок — выдаёт сессионную cookie/JWT               │
│  5. Сохраняет/обновляет запись в Supabase users              │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
              ┌────────────────┐
              │   Supabase     │
              │   table users  │
              │   - telegram_id│
              │   - first_seen │
              │   - last_seen  │
              │   - role       │
              └────────────────┘
```

## Спецификация

### Шаги настройки бота

1. У пользователя в Telegram: `@BotFather` → `/newbot` → имя `cdp_generation_bot` (или подобное)
2. BotFather выдаёт `TELEGRAM_BOT_TOKEN` — кладём в `.env`
3. У BotFather: `/setdomain` → указать домен сайта (например, `cdp-gen.example.com`). **Без этого виджет не будет работать на сайте.**

### Переменные окружения

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...           # из BotFather
TELEGRAM_BOT_USERNAME=cdp_generation_bot          # без @
ALLOWED_TELEGRAM_IDS=123456789,987654321          # через запятую
TELEGRAM_AUTH_TIMEOUT_SECONDS=86400               # сутки на жизнь сессии
```

### Алгоритм валидации подписи (псевдокод)

```python
import hashlib
import hmac
from typing import Any

def verify_telegram_auth(data: dict[str, Any], bot_token: str) -> bool:
    """Проверка HMAC по официальному алгоритму Telegram Login Widget."""
    received_hash = data.pop("hash", None)
    if received_hash is None:
        return False

    # 1. Сортируем по алфавиту, склеиваем в data_check_string
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(data.items())
    )

    # 2. Секретный ключ = SHA-256 от bot_token
    secret_key = hashlib.sha256(bot_token.encode()).digest()

    # 3. Вычисляем HMAC и сравниваем с присланным hash
    computed_hash = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed_hash, received_hash)
```

> ⚠️ Перед реализацией кода — обязательно сверить актуальный алгоритм через **Context7 MCP** по запросу «Telegram Login Widget» или «pyTelegramBotAPI». Алгоритм в спецификации Telegram может уточняться.

### Allow-list

```python
allowed_ids: set[int] = {
    int(x) for x in os.getenv("ALLOWED_TELEGRAM_IDS", "").split(",") if x.strip()
}

def is_allowed(telegram_id: int) -> bool:
    return telegram_id in allowed_ids
```

В фазе 2 первый allow-list — это один Telegram ID самого пользователя.

### Жизненный цикл сессии

1. Виджет отдаёт user-payload → backend валидирует подпись
2. Backend выдаёт session-cookie или JWT (TTL = `TELEGRAM_AUTH_TIMEOUT_SECONDS`)
3. На каждый запрос — middleware проверяет cookie/JWT
4. При истечении — редирект на страницу с виджетом

## Безопасность

- **HMAC-валидация обязательна.** Без неё allow-list бессмыслен — кто угодно может прислать `{"id": <разрешённый_id>}` руками.
- **`auth_date` валидируется** — payload старше суток отклонять (защита от replay).
- **`TELEGRAM_BOT_TOKEN` никогда не попадает на frontend.** Только серверная проверка.
- **Allow-list в env, не в коде.** Чтобы менять без релиза.
- **Логирование попыток входа** в Supabase (успех/неудача, timestamp, telegram_id, IP) — для аудита.

## Границы

- Нет регистрации — только allow-list. Не нужен self-service onboarding.
- Нет recovery — если потерян аккаунт Telegram, восстановление вручную (пользователь добавляет новый Telegram ID в env).
- Нет multi-device sessions — каждый вход с нового устройства создаёт новую сессию.

## Что НЕ делать в фазе 1

- Не имплементировать Telegram-auth в локальной версии. Это лишняя работа: на localhost пользователь и так один.
