"""Pipeline-оркестратор: связывает агентов в один проход."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from src.agents import (
    data_scout,
    doc_keeper,
    intro_writer,
    pdf_renderer,
    reviewer,
    scenario_author,
    visual_designer,
)
from src.exceptions import PDFRenderError
from src.models import GenerationRequest, GenerationResult, IntroPair, IntroRequest, PricingBlock

log = logging.getLogger(__name__)

ProgressFn = Callable[[str, float], None]


def _noop(_msg: str, _pct: float) -> None: ...


def generate(req: GenerationRequest, *, progress: ProgressFn | None = None) -> GenerationResult:
    """Запустить весь pipeline и вернуть GenerationResult.

    `progress(message, percent)` вызывается на каждом шаге — удобно для Streamlit.
    """
    p = progress or _noop

    p("Парсим сайт клиента и собираем факты…", 0.05)
    facts = data_scout.run(req)

    p("Анализируем бриф и подбираем отраслевую карту…", 0.20)
    brief = doc_keeper.parse_brief(req, facts)
    industry_map = doc_keeper.pick_industry_map(req, facts)
    cases = doc_keeper.pick_cases(facts, brief)

    p("Генерируем сценарии (Claude Opus, ~1–2 минуты)…", 0.35)
    pack = scenario_author.run(
        facts=facts,
        brief=brief,
        industry=industry_map,
        cases=cases,
        target_count=req.target_scenarios_count,
    )

    pricing = PricingBlock(
        cdp_price_from=10_500,
        big_data_price_from=5_000,
        additional_products=["big_data"] if any(
            tr.type == "interest_detected" for sc in pack.scenarios for tr in sc.triggers
        ) else [],
        notes=(
            "Старт пилота — от 10 500 ₽/мес. Все сценарии настраиваются под ключ "
            "силами Calltouch (включено в абонплату). Интеграция с CRM — бесплатно."
        ),
    )

    result = GenerationResult(
        request_id=req.request_id,
        client_name=facts.company_name or facts.primary_domain,
        industry=facts.industry_detected,
        target_segments=pack.target_segments,
        site_facts=facts,
        brief_facts=brief,
        scenarios=pack.scenarios,
        cases=cases,
        pricing=pricing,
        next_steps=pack.next_steps,
        no_go_list=pack.no_go_list or brief.explicit_no_go,
    )

    p("Прогоняем ревью по обязательным правилам…", 0.70)
    verdict = reviewer.run(result, brief_text=req.brief)
    result.review_passed = verdict.passed
    result.review_issues = verdict.issues
    if not verdict.passed:
        log.warning("reviewer: найдены ошибки: %s", [i.message for i in verdict.errors])

    p("Собираем HTML по фирменному шаблону…", 0.82)
    result.html_path = visual_designer.render(result)

    p("Печатаем PDF (headless Chrome/Edge)…", 0.92)
    try:
        result.pdf_path = pdf_renderer.render(result.html_path)
    except PDFRenderError as exc:
        log.warning("PDF-рендер упал: %s. Останется только HTML.", exc)
        result.pdf_path = None

    p("Готово.", 1.0)
    return result


def generate_intro(req: IntroRequest, *, progress: ProgressFn | None = None) -> IntroPair:
    """Сгенерировать короткий «цепляющий заход» (Telegram + Email)."""
    p = progress or _noop

    p("Парсим сайт клиента…", 0.10)
    facts = data_scout.collect_facts(
        primary_url=str(req.client_url),
        additional_urls=[str(u) for u in req.additional_urls],
        industry_hint=req.industry_hint,
    )

    p("Пишем intro для Telegram и Email (Claude Opus, ~30 сек)…", 0.50)
    draft = intro_writer.run(req=req, facts=facts)

    pair = IntroPair(
        request_id=req.request_id,
        client_name=draft.client_name or facts.company_name or facts.primary_domain,
        industry=draft.industry or facts.industry_detected,
        telegram_version=draft.telegram_version,
        email_version=draft.email_version,
        scenarios_pitched=draft.scenarios_pitched,
    )
    p("Готово.", 1.0)
    return pair


def to_summary(result: GenerationResult) -> dict[str, Any]:
    """Короткое представление для UI/логов."""
    return {
        "client": result.client_name,
        "industry": result.industry,
        "scenarios": [s.title for s in result.scenarios],
        "review_passed": result.review_passed,
        "issues": [i.message for i in result.review_issues],
        "html": str(result.html_path) if result.html_path else None,
        "pdf": str(result.pdf_path) if result.pdf_path else None,
    }
