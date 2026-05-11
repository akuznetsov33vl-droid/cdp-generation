from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import Action, GenerationRequest, Scenario, ScenarioMetric, Trigger


def test_generation_request_minimal() -> None:
    req = GenerationRequest(
        client_url="https://example.com",  # type: ignore[arg-type]
        brief="бриф длиной более пятидесяти символов чтобы пройти валидацию формы UI",
    )
    assert req.target_scenarios_count == 5
    assert req.client_url.host == "example.com"


def test_target_count_bounds() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            client_url="https://example.com",  # type: ignore[arg-type]
            brief="бриф",
            target_scenarios_count=20,
        )


def test_trigger_action_literals() -> None:
    Trigger(type="page_view", config={"url_pattern": "/foo/*"})
    Action(type="email_to_manager")
    with pytest.raises(ValidationError):
        Trigger(type="not_a_real_trigger", config={})  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Action(type="cold_call")  # type: ignore[arg-type]


def test_scenario_min_metrics() -> None:
    sc = Scenario(
        title="Test",
        pitch="Pitch.",
        audience="Audience.",
        triggers=[Trigger(type="page_view")],
        actions=[Action(type="tag_client")],
        logic_pseudocode="A → B",
        why_calltouch="Because.",
        gives_to_client=["g1"],
        expected_metrics=[ScenarioMetric(label="L", value="V")],
    )
    assert sc.tag == "standard"

    with pytest.raises(ValidationError):
        Scenario(
            title="Test",
            pitch="Pitch.",
            audience="Audience.",
            triggers=[Trigger(type="page_view")],
            actions=[Action(type="tag_client")],
            logic_pseudocode="A → B",
            why_calltouch="Because.",
            gives_to_client=["g1"],
            expected_metrics=[],
        )
