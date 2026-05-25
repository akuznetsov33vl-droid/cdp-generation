"""Тонкая обёртка над Anthropic SDK с поддержкой JSON-вывода через Pydantic."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import TypeVar

from anthropic import Anthropic, APIError, APIStatusError
from pydantic import BaseModel, ValidationError

from src.config import get_settings
from src.exceptions import LLMError, LLMParseError

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_FENCE_OPEN_RE = re.compile(r"```(?:json)?\s*", re.IGNORECASE)


def _client() -> Anthropic:
    settings = get_settings()
    return Anthropic(api_key=settings.anthropic_api_key.get_secret_value())


def _retry_call(fn, *, max_retries: int = 3) -> object:
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except APIStatusError as exc:
            last_err = exc
            if exc.status_code in {429, 500, 502, 503, 504}:
                wait = 2**attempt
                log.warning("LLM transient %s; retry in %ss", exc.status_code, wait)
                time.sleep(wait)
                continue
            raise LLMError(f"Anthropic API status {exc.status_code}: {exc}") from exc
        except APIError as exc:
            last_err = exc
            wait = 2**attempt
            log.warning("LLM API error %s; retry in %ss", exc, wait)
            time.sleep(wait)
    raise LLMError(f"Anthropic API failed after {max_retries} retries: {last_err}")


def call_text(
    *,
    model: str,
    system: str,
    user: str,
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> str:
    """Вызов Claude → возвращает текст из первого `text` блока.

    `temperature` не передаётся в API по умолчанию: для extended-thinking-моделей
    (Opus 4.7) параметр deprecated. Если нужно — явно передай число.
    """
    client = _client()

    kwargs: dict[str, object] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    if temperature is not None:
        kwargs["temperature"] = temperature

    def _do() -> object:
        return client.messages.create(**kwargs)  # type: ignore[arg-type]

    msg = _retry_call(_do)
    parts: list[str] = []
    for block in msg.content:  # type: ignore[attr-defined]
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _strip_fence(raw: str) -> str:
    """Достать тело JSON из ответа LLM, даже если он не идеален:
    - обёрнут в ```json ... ```
    - открыт fence, но не закрыт (обрезался на max_tokens)
    - окружён комментариями/markdown сверху и снизу
    """
    text = raw.strip()
    m = _FENCE_RE.search(text)
    if m:
        return m.group(1).strip()
    text = _FENCE_OPEN_RE.sub("", text, count=1)
    text = text.rstrip("`").rstrip()
    start = text.find("{")
    if start == -1:
        return text
    end = text.rfind("}")
    if end > start:
        return text[start : end + 1]
    return text[start:]


def call_json(
    *,
    model: str,
    system: str,
    user: str,
    schema: type[T],
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> T:
    """Вызов Claude с просьбой вернуть JSON; парсим через Pydantic.

    Anthropic поддерживает структурированный вывод через tool_use, но для лаконичности
    здесь используется prompt-injection с JSON-only ответом — этого достаточно для
    наших агентов и не требует tool_choice-механики.
    """
    json_system = (
        system
        + "\n\nВажно: ОТВЕТЬ СТРОГО ВАЛИДНЫМ JSON-объектом, который соответствует "
        + "схеме модели. Никаких пояснений, заголовков или markdown-обёрток вне JSON. "
        + "Если поле не известно — поставь null или пустой список."
    )
    raw = call_text(
        model=model,
        system=json_system,
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    body = _strip_fence(raw)
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMParseError(f"LLM вернул невалидный JSON: {exc}\nОтвет: {body[:500]}") from exc
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise LLMParseError(f"JSON не прошёл схему {schema.__name__}: {exc}") from exc
