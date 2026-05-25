from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import EmailIntro, IntroPair, IntroRequest, IntroScenarioPitch


def test_intro_request_minimal() -> None:
    req = IntroRequest(client_url="https://example.com")  # type: ignore[arg-type]
    assert req.recipient_name is None
    assert req.sender_name is None
    assert req.brief == ""
    assert req.scenarios_count == 2


def test_intro_request_accepts_all_fields() -> None:
    req = IntroRequest(
        client_url="https://example.com",  # type: ignore[arg-type]
        recipient_name="Пётр",
        recipient_role="директор по маркетингу",
        sender_name="Александр",
        brief="звонили в среду, интересует CDP",
        industry_hint="онлайн-школа",
        scenarios_count=3,
    )
    assert req.recipient_name == "Пётр"
    assert req.sender_name == "Александр"
    assert req.scenarios_count == 3


def test_scenarios_count_bounds() -> None:
    with pytest.raises(ValidationError):
        IntroRequest(client_url="https://example.com", scenarios_count=0)  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        IntroRequest(client_url="https://example.com", scenarios_count=4)  # type: ignore[arg-type]


def test_email_intro_subject_length() -> None:
    EmailIntro(subject="Привет", body="...")
    with pytest.raises(ValidationError):
        EmailIntro(subject="x" * 121, body="...")


def test_intro_pair_round_trip() -> None:
    from uuid import uuid4

    pair = IntroPair(
        request_id=uuid4(),
        client_name="ExampleCo",
        industry="онлайн-школы",
        telegram_version="Привет, Пётр! ...",
        email_version=EmailIntro(subject="ExampleCo: 2 идеи", body="Здравствуйте, Пётр!"),
        scenarios_pitched=[
            IntroScenarioPitch(title="A", one_liner="полезен раз"),
            IntroScenarioPitch(title="B", one_liner="полезен два"),
        ],
    )
    dumped = pair.model_dump_json()
    assert "ExampleCo" in dumped
    assert "телеграм" not in dumped.lower() or "Пётр" in dumped
