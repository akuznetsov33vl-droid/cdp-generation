"""scenario-author — творческое ядро. Генерирует список сценариев через Opus."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from src.config import get_settings
from src.llm import call_json
from src.models import (
    BriefFacts,
    CaseReference,
    IndustryMap,
    Scenario,
    SiteFacts,
)
from src.prompts import load_prompt

log = logging.getLogger(__name__)


class _ScenarioPack(BaseModel):
    """Контейнер списка для удобного JSON-ответа."""

    target_segments: list[str] = []
    next_steps: list[str] = []
    no_go_list: list[str] = []
    scenarios: list[Scenario]


def run(
    *,
    facts: SiteFacts,
    brief: BriefFacts,
    industry: IndustryMap,
    cases: list[CaseReference],
    target_count: int,
) -> _ScenarioPack:
    settings = get_settings()
    prompt = load_prompt("scenario_author")

    user_msg = prompt.format(
        site_facts=facts.model_dump_json(indent=2),
        brief_facts=brief.model_dump_json(indent=2),
        industry_map=industry.model_dump_json(indent=2),
        cases=("\n".join(f"- {c.title}: {c.applicability_to_this_client}" for c in cases)
               or "(подходящих кейсов не найдено)"),
        target_count=target_count,
    )

    pack = call_json(
        model=settings.anthropic_model_opus,
        system=(
            "Ты — scenario-author проекта CDP Generation. Создаёшь уникальные, "
            "реализуемые сценарии Calltouch CDP с учётом архитектуры конкретного клиента "
            "и обязательных правил из docs/spec.md."
        ),
        user=user_msg,
        schema=_ScenarioPack,
        max_tokens=8192,
    )
    log.info("scenario-author: получили %d сценариев", len(pack.scenarios))
    return pack


def expose() -> type[_ScenarioPack]:
    """Для тестов и оркестратора."""
    return _ScenarioPack
