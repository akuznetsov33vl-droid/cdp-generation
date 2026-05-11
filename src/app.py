"""Streamlit-интерфейс CDP Generation (фаза 1)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings  # noqa: E402
from src.exceptions import CDPGenerationError, ConfigError  # noqa: E402
from src.models import GenerationRequest  # noqa: E402
from src.orchestrator import generate  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

st.set_page_config(
    page_title="CDP Generation · Calltouch",
    page_icon="🟣",
    layout="wide",
)

st.markdown(
    """
    <style>
      .stApp h1 { color: #5B2FBF; }
      .stApp .stButton > button {
        background: linear-gradient(135deg, #5B2FBF 0%, #0EA5C7 100%);
        color: white; font-weight: 600; border: none; padding: 8px 24px;
      }
      .stApp .stButton > button:hover { filter: brightness(1.05); }
      .ct-pill {
        display: inline-block; padding: 2px 10px; border-radius: 12px;
        background: #F2EDFF; color: #5B2FBF; font-weight: 600; font-size: 0.85rem;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("CDP Generation")
st.caption("AI-инструмент для индивидуальных коммерческих предложений Calltouch CDP")


def _check_password() -> bool:
    """Простой пароль-gate. Пароль читается из st.secrets['app_password']
    (Streamlit Cloud) или из env STREAMLIT_PASSWORD (локальный/Render).
    Если ни то ни другое не задано — без auth (для локальной разработки)."""
    import os

    expected = None
    try:
        expected = st.secrets.get("app_password")  # type: ignore[attr-defined]
    except (FileNotFoundError, KeyError):
        expected = None
    if not expected:
        expected = os.environ.get("STREAMLIT_PASSWORD")
    if not expected:
        return True

    if st.session_state.get("auth_ok"):
        return True

    st.markdown("### Доступ по паролю")
    pwd = st.text_input("Пароль", type="password", key="pwd_input")
    if st.button("Войти", type="primary"):
        if pwd == expected:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Неверный пароль.")
    st.stop()


_check_password()

try:
    settings = get_settings()
except (ConfigError, ValueError) as exc:
    st.error(f"Ошибка конфигурации: {exc}")
    st.info("Проверь, что ANTHROPIC_API_KEY задан в окружении (Streamlit Secrets / .env).")
    st.stop()

st.markdown(f'<span class="ct-pill">Opus: {settings.anthropic_model_opus}</span> '
            f'<span class="ct-pill">Haiku: {settings.anthropic_model_haiku}</span>',
            unsafe_allow_html=True)

with st.form("generation_form", clear_on_submit=False):
    col_url, col_count = st.columns([3, 1])
    with col_url:
        client_url = st.text_input(
            "URL клиента",
            placeholder="https://level.ru",
            help="Главный домен сайта клиента",
        )
        additional_raw = st.text_input(
            "Дополнительные домены (через запятую, опционально)",
            placeholder="https://business.level.ru, https://srub-lw.ru",
        )
    with col_count:
        scenarios_count = st.number_input(
            "Сколько сценариев",
            min_value=3, max_value=10,
            value=settings.target_scenarios_count,
            step=1,
        )
        industry_hint = st.text_input(
            "Отрасль (подсказка)",
            placeholder="премиум-недвижимость",
        )

    brief = st.text_area(
        "Бриф / транскрипт встречи",
        height=260,
        placeholder=(
            "Расшифровка встречи с клиентом, ключевые задачи, "
            "пожелания, ограничения. Чем подробнее — тем точнее КП."
        ),
    )
    extra_notes = st.text_area(
        "Доп. пожелания менеджера (опционально)",
        height=100,
    )

    submitted = st.form_submit_button("Сгенерировать КП")

if submitted:
    if not client_url.strip():
        st.error("URL клиента обязателен.")
        st.stop()
    if not brief.strip() or len(brief.strip()) < 50:
        st.error("Бриф слишком короткий — нужна расшифровка встречи или подробное описание.")
        st.stop()

    additional = [u.strip() for u in additional_raw.split(",") if u.strip()]

    try:
        request = GenerationRequest(
            client_url=client_url.strip(),  # type: ignore[arg-type]
            additional_urls=additional,  # type: ignore[arg-type]
            brief=brief.strip(),
            extra_notes=extra_notes.strip() or None,
            industry_hint=industry_hint.strip() or None,
            target_scenarios_count=int(scenarios_count),
        )
    except ValueError as exc:
        st.error(f"Невалидные параметры: {exc}")
        st.stop()

    progress_bar = st.progress(0.0, text="Стартуем pipeline…")
    log_box = st.empty()
    log_lines: list[str] = []

    def _progress(msg: str, pct: float) -> None:
        log_lines.append(f"• {msg}")
        log_box.markdown("\n".join(log_lines))
        progress_bar.progress(min(pct, 1.0), text=msg)

    try:
        result = generate(request, progress=_progress)
    except CDPGenerationError as exc:
        progress_bar.empty()
        st.error(f"Ошибка генерации: {exc}")
        st.stop()
    except Exception as exc:  # noqa: BLE001
        progress_bar.empty()
        st.exception(exc)
        st.stop()

    progress_bar.empty()
    if result.review_passed:
        st.success(f"КП готово · {len(result.scenarios)} сценариев · ревью пройдено.")
    else:
        st.warning(f"КП готово, но ревью нашёл замечания: {len(result.review_issues)} шт.")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Клиент", result.client_name)
        st.metric("Отрасль", result.industry)
        st.metric("Сценариев", len(result.scenarios))
    with col_b:
        if result.html_path:
            st.download_button(
                "📄 Скачать HTML",
                data=result.html_path.read_bytes(),
                file_name=result.html_path.name,
                mime="text/html",
            )
        if result.pdf_path:
            st.download_button(
                "📑 Скачать PDF",
                data=result.pdf_path.read_bytes(),
                file_name=result.pdf_path.name,
                mime="application/pdf",
            )
        else:
            st.info(
                "PDF не сгенерирован (Chrome/Edge не найден). "
                "HTML можно открыть в браузере и распечатать в PDF вручную."
            )

    if result.review_issues:
        with st.expander("Замечания ревьюера", expanded=not result.review_passed):
            for issue in result.review_issues:
                icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.severity, "•")
                where = f" ({issue.where})" if issue.where else ""
                st.markdown(f"{icon} **{issue.severity}**{where}: {issue.message}")

    with st.expander("Сценарии (заголовки)"):
        for i, sc in enumerate(result.scenarios, 1):
            st.markdown(f"**{i}. {sc.title}** — _{sc.pitch}_")

    with st.expander("Сырые факты с сайта"):
        st.json(result.site_facts.model_dump(mode="json"))
