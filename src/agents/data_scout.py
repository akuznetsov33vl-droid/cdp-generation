"""data-scout — парсит сайт клиента и достаёт структурированные факты."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from src.config import get_settings
from src.exceptions import ScrapeError
from src.llm import call_json
from src.models import GenerationRequest, SiteFacts
from src.prompts import load_prompt

log = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; CDPGenerationBot/0.1; +https://calltouch.ru)"
PAGE_BUDGET = 8
PAGE_TEXT_LIMIT = 6000


def _fetch(url: str, *, timeout: float = 20.0) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "ru,en;q=0.7"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.text


def _extract_text(html: str) -> tuple[str, list[tuple[str, str]]]:
    soup = BeautifulSoup(html, "lxml")
    for bad in soup(["script", "style", "noscript", "svg"]):
        bad.decompose()

    title = (soup.title.string or "").strip() if soup.title else ""
    body_text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:PAGE_TEXT_LIMIT]

    links: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        if text and len(text) < 80:
            links.append((text, a["href"]))
    return f"TITLE: {title}\n{body_text}", links


def _is_internal(base: str, candidate: str) -> bool:
    try:
        return urlparse(candidate).netloc in {"", urlparse(base).netloc}
    except ValueError:
        return False


def _pick_relevant_links(base: str, links: list[tuple[str, str]]) -> list[str]:
    keywords = (
        "проект",
        "об ",
        "about",
        "team",
        "команд",
        "контакт",
        "contact",
        "цен",
        "price",
        "product",
        "услуг",
        "тариф",
        "case",
        "кейс",
        "клиент",
        "produc",
    )
    seen: set[str] = set()
    result: list[str] = []
    for text, href in links:
        text_low = text.lower()
        if not any(k in text_low for k in keywords):
            continue
        absolute = urljoin(base, href).split("#", 1)[0]
        if absolute in seen:
            continue
        if not _is_internal(base, absolute):
            continue
        seen.add(absolute)
        result.append(absolute)
        if len(result) >= PAGE_BUDGET:
            break
    return result


def _crawl(urls: Iterable[str]) -> str:
    """Скачать главную и до PAGE_BUDGET внутренних страниц, склеить текст."""
    bundles: list[str] = []
    for url in urls:
        try:
            html = _fetch(url)
        except (httpx.HTTPError, httpx.InvalidURL) as exc:
            log.warning("scout: не удалось скачать %s: %s", url, exc)
            continue

        text, links = _extract_text(html)
        bundles.append(f"=== ИСХОДНАЯ СТРАНИЦА: {url} ===\n{text}")

        for sub in _pick_relevant_links(url, links):
            try:
                sub_html = _fetch(sub, timeout=15.0)
            except httpx.HTTPError:
                continue
            sub_text, _ = _extract_text(sub_html)
            bundles.append(f"=== СВЯЗАННАЯ СТРАНИЦА: {sub} ===\n{sub_text}")

    if not bundles:
        raise ScrapeError("Не удалось скачать ни одной страницы клиента.")
    return "\n\n".join(bundles)[:60_000]


def run(req: GenerationRequest) -> SiteFacts:
    settings = get_settings()
    primary = str(req.client_url)
    extra = [str(u) for u in req.additional_urls]
    log.info("scout: краулим %s + %s доп. доменов", primary, len(extra))

    blob = _crawl([primary, *extra])

    prompt_template = load_prompt("data_scout_extract")
    user_msg = prompt_template.format(
        primary_domain=primary,
        additional_domains=", ".join(extra) if extra else "(нет)",
        industry_hint=req.industry_hint or "(не указано)",
        site_blob=blob,
    )

    facts = call_json(
        model=settings.anthropic_model_haiku,
        system=(
            "Ты — data-scout проекта CDP Generation. Извлекаешь структурированные "
            "факты с сайта клиента строго по предоставленному содержимому."
        ),
        user=user_msg,
        schema=SiteFacts,
        max_tokens=4096,
    )
    if not facts.primary_domain:
        facts.primary_domain = primary
    if extra and not facts.additional_domains:
        facts.additional_domains = extra
    return facts
