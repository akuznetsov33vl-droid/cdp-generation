"""intro-writer — короткое intro-сообщение для холодного контакта.

Принимает SiteFacts (от data-scout) и параметры письма, возвращает пару
(Telegram-версия + Email-версия) с упоминанием N сценариев под бизнес клиента.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from src.config import get_settings
from src.llm import call_json
from src.models import EmailIntro, IntroRequest, IntroScenarioPitch, SiteFacts
from src.prompts import load_prompt

log = logging.getLogger(__name__)


class _IntroDraft(BaseModel):
    """Сырой ответ Opus — без UUID/timestamp, их добавит orchestrator."""

    client_name: str
    industry: str
    scenarios_pitched: list[IntroScenarioPitch]
    telegram_version: str
    email_version: EmailIntro


def run(*, req: IntroRequest, facts: SiteFacts) -> _IntroDraft:
    settings = get_settings()
    prompt = load_prompt("cold_intro")

    user_msg = prompt.format(
        site_facts=facts.model_dump_json(indent=2),
        brief=(req.brief.strip() or "(не указан)"),
        recipient_name=(req.recipient_name or "(не указано)"),
        recipient_role=(req.recipient_role or "(не указано)"),
        sender_name=(req.sender_name or "(не указано)"),
        scenarios_count=req.scenarios_count,
        industry_hint=(req.industry_hint or "(не указана)"),
    )

    draft = call_json(
        model=settings.anthropic_model_opus,
        system=(
            "Ты — мастер холодных заходов проекта CDP Generation. Пишешь короткие "
            "продающие встречу intro-сообщения для email и Telegram. Главный приём — "
            "показать клиенту, что мы уже знаем его бизнес и видим конкретные сценарии."
        ),
        user=user_msg,
        schema=_IntroDraft,
        max_tokens=3072,
    )

    if len(draft.scenarios_pitched) != req.scenarios_count:
        log.warning(
            "intro-writer: запросили %d сценариев, получили %d — отдаём как есть",
            req.scenarios_count,
            len(draft.scenarios_pitched),
        )
    return draft
