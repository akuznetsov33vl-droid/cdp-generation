"""visual-designer — рендер HTML из Jinja-шаблона."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import get_settings
from src.models import GenerationResult

log = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "j2"]),
    trim_blocks=False,
    lstrip_blocks=False,
)


_CYR_TO_LAT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})


def _client_slug(name: str) -> str:
    transliterated = name.lower().translate(_CYR_TO_LAT)
    cleaned = "".join(ch if ch.isascii() and ch.isalnum() else "_" for ch in transliterated)
    cleaned = "_".join(filter(None, cleaned.split("_")))
    return cleaned or "client"


def render(result: GenerationResult) -> Path:
    settings = get_settings()
    template = _env.get_template("proposal.html.j2")
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
    out_path = settings.output_dir / f"{_client_slug(result.client_name)}_CDP_Proposal.html"
    out_path.write_text(html, encoding="utf-8")
    log.info("visual-designer: HTML сохранён в %s", out_path)
    return out_path
