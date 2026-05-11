"""pdf-renderer — печать HTML в PDF.

Стратегия: WeasyPrint (для cloud-деплоя, чистый Python+system libs) →
если не установлен/упал → fallback на headless Chrome/Edge (локальная разработка).
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from src.config import get_settings
from src.exceptions import ConfigError, PDFRenderError

log = logging.getLogger(__name__)


def _try_weasyprint(html_path: Path, pdf_path: Path) -> bool:
    try:
        from weasyprint import HTML
    except ImportError:
        log.info("pdf: weasyprint не установлен, пробуем Chrome")
        return False
    except OSError as exc:
        log.info("pdf: weasyprint не загрузился (нет нативных libs): %s", exc)
        return False

    try:
        HTML(filename=str(html_path)).write_pdf(str(pdf_path))
    except Exception as exc:  # noqa: BLE001
        log.warning("pdf: weasyprint упал: %s", exc)
        return False
    return True


def _try_chrome(html_path: Path, pdf_path: Path) -> bool:
    settings = get_settings()
    try:
        browser = settings.detect_browser()
    except ConfigError as exc:
        log.info("pdf: chrome/edge не найден: %s", exc)
        return False

    file_url = html_path.resolve().as_uri()
    cmd = [
        str(browser),
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        file_url,
    ]
    log.info("pdf: chrome %s → %s", browser.name, pdf_path)
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    except (FileNotFoundError, PermissionError, OSError) as exc:
        log.warning("pdf: subprocess fail %s", exc)
        return False
    except subprocess.TimeoutExpired:
        log.warning("pdf: chrome timeout 120s")
        return False

    if proc.returncode != 0 and not pdf_path.exists():
        log.warning("pdf: chrome rc=%s stderr=%s", proc.returncode, proc.stderr[:200])
        return False
    return pdf_path.exists()


def render(html_path: Path) -> Path:
    pdf_path = html_path.with_suffix(".pdf")

    if _try_weasyprint(html_path, pdf_path):
        log.info("pdf: weasyprint OK → %s", pdf_path)
        return pdf_path

    if _try_chrome(html_path, pdf_path):
        log.info("pdf: chrome OK → %s", pdf_path)
        return pdf_path

    raise PDFRenderError(
        "Не удалось отрендерить PDF: ни WeasyPrint, ни Chrome/Edge не сработали. "
        "Локально: установи Chrome или GTK для WeasyPrint. "
        "На Streamlit Cloud: проверь packages.txt (libpango, libharfbuzz, libfontconfig)."
    )
