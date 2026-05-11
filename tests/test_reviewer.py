from __future__ import annotations

from uuid import uuid4

from src.agents import reviewer
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


def _stub_facts() -> SiteFacts:
    return SiteFacts(primary_domain="https://example.com", industry_detected="test")


def _stub_brief() -> BriefFacts:
    return BriefFacts(main_kpi="kpi")


def _make_scenario(**overrides) -> Scenario:
    base = dict(
        title="Sc1",
        pitch="Pitch",
        audience="Aud",
        triggers=[Trigger(type="page_view", config={})],
        actions=[Action(type="email_to_manager", config={})],
        logic_pseudocode="A → B",
        why_calltouch="Because",
        gives_to_client=["g1"],
        expected_metrics=[ScenarioMetric(label="x", value="y")],
    )
    base.update(overrides)
    return Scenario(**base)


def _make_result(scenarios: list[Scenario], pricing: PricingBlock | None = None) -> GenerationResult:
    return GenerationResult(
        request_id=uuid4(),
        client_name="X",
        industry="test",
        site_facts=_stub_facts(),
        brief_facts=_stub_brief(),
        scenarios=scenarios,
        pricing=pricing or PricingBlock(),
    )


def test_clean_scenario_passes() -> None:
    result = _make_result([_make_scenario()])
    verdict = reviewer.run(result, brief_text="чистый бриф")
    assert verdict.passed
    assert not verdict.errors


def test_competitor_in_text_blocks() -> None:
    sc = _make_scenario(why_calltouch="Лучше чем Mindbox.")
    result = _make_result([sc])
    verdict = reviewer.run(result, brief_text="бриф без конкурентов")
    assert not verdict.passed
    assert any("mindbox" in i.message.lower() for i in verdict.errors)


def test_competitor_allowed_when_in_brief() -> None:
    sc = _make_scenario(why_calltouch="Похоже на Mindbox.")
    result = _make_result([sc])
    verdict = reviewer.run(
        result,
        brief_text="клиент уже сравнивает с Mindbox и Carrotquest",
    )
    assert verdict.passed


def test_pricing_must_be_canonical() -> None:
    result = _make_result(
        [_make_scenario()],
        pricing=PricingBlock(cdp_price_from=9000, big_data_price_from=5000),
    )
    verdict = reviewer.run(result, brief_text="ok")
    assert not verdict.passed
    assert any("10 500" in i.message for i in verdict.errors)


def test_smart_sms_blocked() -> None:
    sc = _make_scenario(logic_pseudocode="Smart SMS Билайн → клиент")
    result = _make_result([sc])
    verdict = reviewer.run(result, brief_text="ok")
    assert not verdict.passed
    assert any("smart sms" in i.message.lower() for i in verdict.errors)


def test_waba_warning_only() -> None:
    sc = _make_scenario(why_calltouch="Отправляем в WhatsApp.")
    result = _make_result([sc])
    verdict = reviewer.run(result, brief_text="WABA не упоминается")
    waba_issues = [i for i in verdict.issues if "whatsapp" in i.message.lower()]
    assert waba_issues
    assert all(i.severity != "error" for i in waba_issues)
    assert verdict.passed
