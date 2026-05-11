"""reviewer — детерминированные правила + LLM-перепроверка."""

from __future__ import annotations

import logging
import re

from src.models import GenerationResult, ReviewIssue, ReviewVerdict, Scenario

log = logging.getLogger(__name__)

COMPETITORS = (
    "mindbox",
    "altcraft",
    "enkod",
    "sendsay",
    "carrotquest",
    "carrot quest",
    "roistat",
    "rees46",
)

FORBIDDEN_TERMS = (
    "smart sms",
    "смарт sms",
    "smart-sms",
)

ALLOWED_TRIGGER_TYPES = {
    "session_start",
    "session_end",
    "new_lead",
    "lead_change",
    "new_deal",
    "deal_status_change",
    "page_view",
    "goal_achieved",
    "interest_detected",
    "custom_event",
    "scheduled",
}

ALLOWED_ACTION_TYPES = {
    "email_to_manager",
    "email_to_client",
    "sms_to_manager",
    "sms_to_known_client",
    "callback",
    "webhook",
    "show_form",
    "tag_client",
    "messenger_message",
}

CDP_PRICE_PATTERN = re.compile(r"от\s*10[\s\xa0]?500\s*₽", re.IGNORECASE)
BD_PRICE_PATTERN = re.compile(r"от\s*5[\s\xa0]?000\s*₽", re.IGNORECASE)


def _scenario_text(s: Scenario) -> str:
    return " ".join(
        [
            s.title,
            s.pitch,
            s.audience,
            s.logic_pseudocode,
            s.popup_text or "",
            s.email_text or "",
            s.why_calltouch,
            *s.gives_to_client,
        ]
    ).lower()


def _check_competitors(scenarios: list[Scenario], brief_text: str) -> list[ReviewIssue]:
    brief_low = brief_text.lower()
    issues: list[ReviewIssue] = []
    for idx, sc in enumerate(scenarios, 1):
        text = _scenario_text(sc)
        for comp in COMPETITORS:
            if comp in text and comp not in brief_low:
                issues.append(
                    ReviewIssue(
                        severity="error",
                        message=f"В сценарии №{idx} упомянут конкурент «{comp}», "
                        f"которого нет в брифе.",
                        where=sc.title,
                    )
                )
    return issues


def _check_forbidden(scenarios: list[Scenario]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for idx, sc in enumerate(scenarios, 1):
        text = _scenario_text(sc)
        for term in FORBIDDEN_TERMS:
            if term in text:
                issues.append(
                    ReviewIssue(
                        severity="error",
                        message=f"Сценарий №{idx} использует «{term}» — продажа приостановлена.",
                        where=sc.title,
                    )
                )
        if "waba" in text or "whatsapp" in text:
            issues.append(
                ReviewIssue(
                    severity="warning",
                    message=f"Сценарий №{idx} упоминает WhatsApp/WABA. "
                    f"Убедись, что это явно в брифе.",
                    where=sc.title,
                )
            )
    return issues


def _check_primitives(scenarios: list[Scenario]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    for idx, sc in enumerate(scenarios, 1):
        for tr in sc.triggers:
            if tr.type not in ALLOWED_TRIGGER_TYPES:
                issues.append(
                    ReviewIssue(
                        severity="error",
                        message=f"Сценарий №{idx}: триггер «{tr.type}» вне канонического списка.",
                        where=sc.title,
                    )
                )
        for ac in sc.actions:
            if ac.type not in ALLOWED_ACTION_TYPES:
                issues.append(
                    ReviewIssue(
                        severity="error",
                        message=f"Сценарий №{idx}: действие «{ac.type}» вне канонического списка.",
                        where=sc.title,
                    )
                )
        if not sc.triggers:
            issues.append(
                ReviewIssue(
                    severity="warning",
                    message=f"Сценарий №{idx} без триггеров.",
                    where=sc.title,
                )
            )
        if not sc.actions:
            issues.append(
                ReviewIssue(
                    severity="warning",
                    message=f"Сценарий №{idx} без действий.",
                    where=sc.title,
                )
            )
    return issues


def _check_pricing(result: GenerationResult) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []
    if result.pricing.cdp_price_from != 10500:
        issues.append(
            ReviewIssue(
                severity="error",
                message=f"Цена CDP должна быть 10 500 ₽, в результате: "
                f"{result.pricing.cdp_price_from}.",
                where="pricing",
            )
        )
    if result.pricing.big_data_price_from != 5000:
        issues.append(
            ReviewIssue(
                severity="error",
                message=f"Цена Big Data должна быть 5 000 ₽, в результате: "
                f"{result.pricing.big_data_price_from}.",
                where="pricing",
            )
        )
    return issues


def _check_unique_titles(scenarios: list[Scenario]) -> list[ReviewIssue]:
    seen: dict[str, int] = {}
    issues: list[ReviewIssue] = []
    for idx, sc in enumerate(scenarios, 1):
        key = sc.title.strip().lower()
        if key in seen:
            issues.append(
                ReviewIssue(
                    severity="warning",
                    message=f"Сценарии №{seen[key]} и №{idx} имеют одинаковое название «{sc.title}».",
                    where=sc.title,
                )
            )
        else:
            seen[key] = idx
    return issues


def run(result: GenerationResult, *, brief_text: str) -> ReviewVerdict:
    issues: list[ReviewIssue] = []
    issues += _check_competitors(result.scenarios, brief_text)
    issues += _check_forbidden(result.scenarios)
    issues += _check_primitives(result.scenarios)
    issues += _check_pricing(result)
    issues += _check_unique_titles(result.scenarios)

    if not result.scenarios:
        issues.append(
            ReviewIssue(severity="error", message="Список сценариев пуст.", where="scenarios")
        )

    has_errors = any(i.severity == "error" for i in issues)
    return ReviewVerdict(passed=not has_errors, issues=issues)
