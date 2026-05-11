"""Smoke-тест: Jinja-шаблон рендерится с минимальными данными."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.agents.visual_designer import TEMPLATES_DIR
from src.models import (
    Action,
    BriefFacts,
    GenerationResult,
    PricingBlock,
    Scenario,
    ScenarioMetric,
    SiteFacts,
    Trigger,
)


def test_template_renders() -> None:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("proposal.html.j2")

    facts = SiteFacts(
        primary_domain="https://example.com",
        company_name="ExampleCo",
        industry_detected="test",
        raw_summary="Это тестовая компания.",
    )
    brief = BriefFacts(main_kpi="Поднять CR", pain_points=["Боль 1"], explicit_no_go=["Без скидок"])
    sc = Scenario(
        title="Sc 1",
        pitch="Это сценарий 1",
        audience="Тестовая аудитория",
        tag="priority",
        triggers=[Trigger(type="page_view", config={"url_pattern": "/foo"})],
        actions=[Action(type="email_to_manager", config={})],
        logic_pseudocode="A → B → C",
        why_calltouch="Потому что CDP",
        gives_to_client=["Преимущество"],
        expected_metrics=[ScenarioMetric(label="CR", value="×1.5")],
    )
    result = GenerationResult(
        request_id=uuid4(),
        client_name="ExampleCo",
        industry="test",
        target_segments=["Сегмент A"],
        site_facts=facts,
        brief_facts=brief,
        scenarios=[sc],
        pricing=PricingBlock(),
        next_steps=["Шаг 1"],
        no_go_list=["Без скидок"],
        generated_at=datetime(2026, 5, 7, 12, 0, 0),
    )

    html = template.render(
        client_name=result.client_name,
        industry=result.industry,
        target_segments=result.target_segments,
        site_facts=result.site_facts,
        brief_facts=result.brief_facts,
        scenarios=result.scenarios,
        pricing=result.pricing,
        next_steps=result.next_steps,
        no_go_list=result.no_go_list,
        generated_at_human=result.generated_at.strftime("%d.%m.%Y"),
    )
    assert "ExampleCo" in html
    assert "Sc 1" in html
    assert "от 10" in html and "500" in html
    assert "Шаг 1" in html
