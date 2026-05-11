"""doc-keeper — простой keyword-RAG поверх локальной cdp_calltouch_kb."""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

from src.config import get_settings
from src.exceptions import ConfigError
from src.llm import call_json
from src.models import (
    BriefFacts,
    CaseReference,
    GenerationRequest,
    IndustryMap,
    SiteFacts,
)
from src.prompts import load_prompt

log = logging.getLogger(__name__)

CASE_DIRS = ("05_cases",)
INDUSTRY_DIRS = ("03_clients", "04_templates")
TOKEN_RE = re.compile(r"[А-Яа-яёЁA-Za-z0-9]{4,}", re.UNICODE)


def _list_md(root: Path, subdirs: tuple[str, ...]) -> list[Path]:
    out: list[Path] = []
    for sub in subdirs:
        sub_root = root / sub
        if not sub_root.exists():
            continue
        out.extend(sorted(sub_root.rglob("*.md")))
    return out


def _tokens(text: str) -> Counter[str]:
    return Counter(t.lower() for t in TOKEN_RE.findall(text))


def _score(query_tokens: Counter[str], doc_text: str) -> int:
    doc_tokens = _tokens(doc_text)
    return sum(min(query_tokens[w], doc_tokens[w]) for w in query_tokens)


def _read_md(path: Path, limit: int = 8000) -> str:
    try:
        return path.read_text(encoding="utf-8")[:limit]
    except OSError:
        return ""


def _load_kb_root() -> Path:
    settings = get_settings()
    root = settings.knowledge_base_path
    if not root.exists():
        raise ConfigError(
            f"Папка базы знаний не найдена: {root}. "
            f"Проверь KNOWLEDGE_BASE_PATH в .env."
        )
    return root


def _retrieve(query: str, candidates: list[Path], top_k: int) -> list[Path]:
    qt = _tokens(query)
    scored: list[tuple[int, Path]] = []
    for path in candidates:
        text = _read_md(path)
        if not text:
            continue
        scored.append((_score(qt, text), path))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for s, p in scored[:top_k] if s > 0]


def parse_brief(req: GenerationRequest, facts: SiteFacts) -> BriefFacts:
    settings = get_settings()
    prompt = load_prompt("doc_keeper_brief")
    user_msg = prompt.format(
        company_name=facts.company_name or "(не определено)",
        industry=facts.industry_detected,
        primary_domain=facts.primary_domain,
        brief=req.brief,
        extra_notes=req.extra_notes or "(нет)",
    )
    return call_json(
        model=settings.anthropic_model_haiku,
        system=(
            "Ты — doc-keeper. Анализируешь свободный бриф/транскрипт менеджера "
            "и достаёшь структурированные факты, KPI, ограничения, no-go."
        ),
        user=user_msg,
        schema=BriefFacts,
        max_tokens=2048,
    )


def pick_industry_map(req: GenerationRequest, facts: SiteFacts) -> IndustryMap:
    root = _load_kb_root()
    candidates = _list_md(root, INDUSTRY_DIRS)
    query = " ".join(
        [
            facts.industry_detected,
            req.industry_hint or "",
            facts.company_name or "",
            (facts.detected_class or ""),
        ]
    )
    matches = _retrieve(query, candidates, top_k=3)
    if not matches:
        return IndustryMap(name=facts.industry_detected, key_scenarios=[], typical_kpis=[])

    primary = matches[0]
    notes = "\n\n".join(_read_md(p, 3000) for p in matches[:3])
    return IndustryMap(
        name=primary.stem,
        source_path=str(primary),
        key_scenarios=[],
        typical_kpis=[],
        notes=notes[:6000],
    )


def pick_cases(facts: SiteFacts, brief: BriefFacts, top_k: int = 3) -> list[CaseReference]:
    root = _load_kb_root()
    candidates = _list_md(root, CASE_DIRS)
    query = " ".join(
        [
            facts.industry_detected,
            facts.company_name or "",
            brief.main_kpi,
            *brief.pain_points,
        ]
    )
    matches = _retrieve(query, candidates, top_k=top_k)
    out: list[CaseReference] = []
    for path in matches:
        text = _read_md(path, 2000)
        nums = re.findall(r"[+×]\s?\d+[%\s\w./]*", text)[:5]
        out.append(
            CaseReference(
                title=path.stem.replace("_", " "),
                source_path=str(path),
                industry=facts.industry_detected,
                key_numbers=nums,
                applicability_to_this_client=text[:500],
            )
        )
    return out
