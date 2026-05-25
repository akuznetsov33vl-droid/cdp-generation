"""Pydantic-модели — единственный источник правды по контрактам данных."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field

ClientClass = Literal["mass", "comfort", "business", "premium", "deluxe"]

TriggerType = Literal[
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
]

ActionType = Literal[
    "email_to_manager",
    "email_to_client",
    "sms_to_manager",
    "sms_to_known_client",
    "callback",
    "webhook",
    "show_form",
    "tag_client",
    "messenger_message",
]


class GenerationRequest(BaseModel):
    model_config = ConfigDict(frozen=False)

    request_id: UUID = Field(default_factory=uuid4)
    client_url: AnyHttpUrl
    additional_urls: list[AnyHttpUrl] = []
    brief: str
    extra_notes: str | None = None
    industry_hint: str | None = None
    target_scenarios_count: int = Field(default=5, ge=3, le=10)


class IntroRequest(BaseModel):
    """Запрос на генерацию «цепляющего захода» — короткого intro-сообщения
    для холодного контакта (email + Telegram) с N короткими сценариями."""

    model_config = ConfigDict(frozen=False)

    request_id: UUID = Field(default_factory=uuid4)
    client_url: AnyHttpUrl
    additional_urls: list[AnyHttpUrl] = []
    recipient_name: str | None = None
    recipient_role: str | None = None
    sender_name: str | None = None
    brief: str = ""
    industry_hint: str | None = None
    scenarios_count: int = Field(default=2, ge=1, le=3)


class EmailIntro(BaseModel):
    subject: str = Field(max_length=120)
    body: str


class IntroScenarioPitch(BaseModel):
    title: str
    one_liner: str


class IntroPair(BaseModel):
    """Финальный артефакт intro: два варианта одного сообщения."""

    request_id: UUID
    client_name: str
    industry: str
    telegram_version: str
    email_version: EmailIntro
    scenarios_pitched: list[IntroScenarioPitch]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ProductRef(BaseModel):
    name: str
    url: str | None = None
    price_from: float | None = None
    description: str | None = None


class ProjectRef(BaseModel):
    name: str
    url: str | None = None
    location: str | None = None
    price_from: float | None = None
    status: str | None = None


class TeamMember(BaseModel):
    name: str
    role: str | None = None


class PricingSignal(BaseModel):
    label: str
    value: str


class ContactBlock(BaseModel):
    # `kind` намеренно str, не Literal: Haiku может вернуть «whatsapp», «zoom»,
    # «mob_phone» — лучше пропустить, чем уронить весь pipeline на парсинге.
    kind: str
    value: str
    note: str | None = None


class SocialChannel(BaseModel):
    # `platform` — str по той же причине: на сайтах встречаются дзен/одноклассники/etc.
    platform: str
    handle: str | None = None
    url: str | None = None
    subscribers: float | None = None


class SiteFacts(BaseModel):
    primary_domain: str
    additional_domains: list[str] = []
    company_name: str | None = None
    industry_detected: str
    detected_class: ClientClass | None = None
    products: list[ProductRef] = []
    projects: list[ProjectRef] = []
    pricing_signals: list[PricingSignal] = []
    team_members: list[TeamMember] = []
    contact_blocks: list[ContactBlock] = []
    social_channels: list[SocialChannel] = []
    detected_crm_hints: list[str] = []
    raw_summary: str = ""


class BriefFacts(BaseModel):
    main_kpi: str
    pain_points: list[str] = []
    constraints: list[str] = []
    explicit_no_go: list[str] = []
    industry_confirmation: str | None = None
    context_from_meeting: str | None = None
    target_segments: list[str] = []


class IndustryMap(BaseModel):
    name: str
    source_path: str | None = None
    key_scenarios: list[str] = []
    typical_kpis: list[str] = []
    notes: str | None = None


class CaseReference(BaseModel):
    title: str
    source_path: str | None = None
    industry: str
    key_numbers: list[str] = []
    applicability_to_this_client: str | None = None


class Trigger(BaseModel):
    type: TriggerType
    config: dict[str, Any] = {}


class Action(BaseModel):
    type: ActionType
    config: dict[str, Any] = {}


class ScenarioMetric(BaseModel):
    label: str
    value: str


class Scenario(BaseModel):
    title: str
    pitch: str
    audience: str
    tag: Literal["priority", "standard", "advanced"] = "standard"
    triggers: list[Trigger] = Field(default_factory=list)
    actions: list[Action] = Field(default_factory=list)
    logic_pseudocode: str
    popup_text: str | None = None
    email_text: str | None = None
    why_calltouch: str
    expected_metrics: list[ScenarioMetric] = Field(default_factory=list, min_length=1, max_length=4)
    gives_to_client: list[str] = Field(default_factory=list, min_length=1)


class PricingBlock(BaseModel):
    cdp_price_from: int = 10500
    big_data_price_from: int = 5000
    additional_products: list[str] = []
    notes: str | None = None


class ReviewIssue(BaseModel):
    severity: Literal["error", "warning", "info"] = "warning"
    message: str
    where: str | None = None


class ReviewVerdict(BaseModel):
    passed: bool
    issues: list[ReviewIssue] = []

    @property
    def errors(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.severity == "error"]


class GenerationResult(BaseModel):
    request_id: UUID
    client_name: str
    industry: str
    target_segments: list[str] = []
    site_facts: SiteFacts
    brief_facts: BriefFacts
    scenarios: list[Scenario]
    cases: list[CaseReference] = []
    pricing: PricingBlock = PricingBlock()
    next_steps: list[str] = []
    no_go_list: list[str] = []
    html_path: Path | None = None
    pdf_path: Path | None = None
    review_passed: bool = False
    review_issues: list[ReviewIssue] = []
    generated_at: datetime = Field(default_factory=datetime.utcnow)
