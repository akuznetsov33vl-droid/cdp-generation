"""Регрессия: каждый промпт можно отформатировать с ожидаемым набором kwargs.

Ловит баги, когда в тексте промпта остаётся незакрытое `{что-то}` — пример для
LLM, который str.format() пытается интерпретировать как плейсхолдер и падает.
"""

from __future__ import annotations

import pytest

from src.prompts import load_prompt

PROMPT_KWARGS = {
    "data_scout_extract": {
        "primary_domain": "https://x",
        "additional_domains": "",
        "industry_hint": "",
        "site_blob": "",
    },
    "doc_keeper_brief": {
        "company_name": "",
        "industry": "",
        "primary_domain": "",
        "brief": "",
        "extra_notes": "",
    },
    "scenario_author": {
        "site_facts": "{}",
        "brief_facts": "{}",
        "industry_map": "{}",
        "cases": "",
        "target_count": 5,
    },
    "cold_intro": {
        "site_facts": "{}",
        "brief": "",
        "recipient_name": "",
        "recipient_role": "",
        "sender_name": "",
        "scenarios_count": 2,
        "industry_hint": "",
    },
}


@pytest.mark.parametrize("prompt_name,kwargs", list(PROMPT_KWARGS.items()))
def test_prompt_format(prompt_name: str, kwargs: dict) -> None:
    template = load_prompt(prompt_name)
    rendered = template.format(**kwargs)
    assert len(rendered) > 100
