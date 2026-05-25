"""Регрессии на устойчивость _strip_fence к мусору вокруг JSON."""

from __future__ import annotations

from src.llm import _strip_fence


def test_clean_json_passes_through() -> None:
    raw = '{"a": 1, "b": "x"}'
    assert _strip_fence(raw) == raw


def test_fenced_json() -> None:
    raw = '```json\n{"a": 1}\n```'
    assert _strip_fence(raw) == '{"a": 1}'


def test_fenced_no_language() -> None:
    raw = '```\n{"a": 1}\n```'
    assert _strip_fence(raw) == '{"a": 1}'


def test_unclosed_fence_at_start() -> None:
    raw = '```json\n{"a": 1, "b": "long"}'
    out = _strip_fence(raw)
    assert out.startswith("{") and out.endswith("}")
    assert "```" not in out


def test_prose_before_and_after_json() -> None:
    raw = 'Конечно, вот результат:\n{"a": 1}\n\nНадеюсь, помог!'
    assert _strip_fence(raw) == '{"a": 1}'


def test_truncated_json_returned_as_best_effort() -> None:
    # Закрывающей `}` нет — функция возвращает всё начиная с первой `{`,
    # дальше json.loads честно упадёт с понятной ошибкой.
    raw = '```json\n{"a": 1, "b": "тут оборвалось'
    out = _strip_fence(raw)
    assert out.startswith("{")
    assert "```" not in out
