"""Streamlit-интерфейс CDP Generation (фаза 1)."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import streamlit as st


def _hydrate_env_from_secrets() -> None:
    """Streamlit Cloud хранит секреты в `st.secrets`, но pydantic-settings
    читает только переменные окружения. Прокидываем явно ДО get_settings().

    Локально (без secrets.toml) `secrets.items()` бросает StreamlitSecretNotFoundError —
    в этом случае спокойно выходим, нечего хайдрировать.
    """
    try:
        items = list(st.secrets.items())
    except Exception:  # noqa: BLE001 — best-effort utility
        return
    for key, value in items:
        if isinstance(value, str) and key not in os.environ:
            os.environ[key] = value


_hydrate_env_from_secrets()

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
    page_icon="🜂",
    layout="wide",
)

_THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;700;900&family=Rajdhani:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --bg-void: #050818;
  --bg-deep: #0a0e2a;
  --bg-card: rgba(12, 18, 48, 0.78);
  --arc-cyan: #00d4ff;
  --arc-glow: #4be0ff;
  --arc-deep: #007ea3;
  --strange-gold: #ffb938;
  --strange-amber: #c98d2a;
  --doom-fire: #ff3d00;
  --doom-ember: #ff7a45;
  --rune-violet: #6c2fb2;
  --text-glow: #e8f1ff;
  --text-dim: #8fa3c8;
}

.stApp {
  background:
    radial-gradient(ellipse at 18% -10%, rgba(108, 47, 178, 0.38) 0%, transparent 50%),
    radial-gradient(ellipse at 82% 110%, rgba(0, 212, 255, 0.22) 0%, transparent 55%),
    radial-gradient(ellipse at 50% 50%, rgba(255, 61, 0, 0.07) 0%, transparent 45%),
    var(--bg-void) !important;
  color: var(--text-glow);
  font-family: 'Rajdhani', 'Segoe UI', sans-serif;
}

.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(0, 212, 255, 0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0, 212, 255, 0.045) 1px, transparent 1px);
  background-size: 42px 42px;
  pointer-events: none;
  z-index: 0;
  mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
}

.stApp::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    radial-gradient(1px 1px at 18% 32%, white, transparent),
    radial-gradient(1px 1px at 78% 68%, rgba(255, 185, 56, 0.7), transparent),
    radial-gradient(1px 1px at 42% 82%, rgba(0, 212, 255, 0.7), transparent),
    radial-gradient(1px 1px at 64% 16%, white, transparent),
    radial-gradient(1px 1px at 88% 42%, rgba(255, 61, 0, 0.5), transparent),
    radial-gradient(1px 1px at 10% 70%, rgba(255, 255, 255, 0.6), transparent),
    radial-gradient(1px 1px at 95% 8%, rgba(108, 47, 178, 0.8), transparent);
  pointer-events: none;
  z-index: 0;
  opacity: 0.7;
  animation: twinkle 9s ease-in-out infinite alternate;
}
@keyframes twinkle {
  0% { opacity: 0.4; }
  100% { opacity: 0.85; }
}

[data-testid="stAppViewContainer"] > * { position: relative; z-index: 1; }

.stApp h1 {
  font-family: 'Orbitron', sans-serif !important;
  font-weight: 900 !important;
  letter-spacing: 0.12em !important;
  text-transform: uppercase;
  font-size: 2.8rem !important;
  background: linear-gradient(180deg, var(--arc-glow) 0%, var(--arc-cyan) 50%, var(--strange-gold) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  text-shadow:
    0 0 25px rgba(0, 212, 255, 0.55),
    0 0 50px rgba(108, 47, 178, 0.4);
  filter: drop-shadow(0 0 6px rgba(255, 185, 56, 0.3));
  margin-bottom: 0 !important;
}

.stApp [data-testid="stCaptionContainer"], .stApp .stCaption {
  color: var(--text-dim) !important;
  font-family: 'Rajdhani', sans-serif;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-size: 0.85rem;
}

.stApp h2, .stApp h3 {
  font-family: 'Orbitron', sans-serif !important;
  color: var(--arc-cyan) !important;
  text-shadow: 0 0 12px rgba(0, 212, 255, 0.5);
  letter-spacing: 0.06em;
}

.stApp label, .stApp .stMarkdown p, .stApp [data-testid="stWidgetLabel"] {
  color: var(--text-glow) !important;
  font-family: 'Rajdhani', sans-serif !important;
  letter-spacing: 0.02em;
}

.stApp .stTextInput input,
.stApp .stTextArea textarea,
.stApp .stNumberInput input {
  background: rgba(5, 8, 24, 0.78) !important;
  color: var(--text-glow) !important;
  border: 1px solid rgba(0, 212, 255, 0.35) !important;
  border-radius: 4px !important;
  font-family: 'Rajdhani', 'JetBrains Mono', monospace !important;
  box-shadow: inset 0 0 12px rgba(0, 212, 255, 0.08);
  transition: all 0.25s ease;
}
.stApp .stTextInput input:focus,
.stApp .stTextArea textarea:focus,
.stApp .stNumberInput input:focus {
  border-color: var(--arc-cyan) !important;
  box-shadow:
    inset 0 0 18px rgba(0, 212, 255, 0.15),
    0 0 18px rgba(0, 212, 255, 0.45),
    0 0 0 1px var(--arc-cyan) !important;
  outline: none !important;
}

.stApp [data-testid="stForm"] {
  background: var(--bg-card) !important;
  border: 1px solid rgba(255, 185, 56, 0.22);
  border-radius: 12px;
  padding: 24px !important;
  box-shadow:
    0 0 0 1px rgba(0, 212, 255, 0.12),
    0 0 60px rgba(108, 47, 178, 0.25),
    inset 0 1px 0 rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  position: relative;
}

.stApp .stButton > button,
.stApp .stDownloadButton > button,
.stApp [data-testid="stFormSubmitButton"] button {
  background: linear-gradient(135deg, var(--arc-cyan) 0%, var(--rune-violet) 55%, var(--doom-fire) 100%) !important;
  color: white !important;
  font-family: 'Orbitron', sans-serif !important;
  font-weight: 700 !important;
  letter-spacing: 0.15em !important;
  text-transform: uppercase !important;
  border: 1px solid var(--arc-cyan) !important;
  border-radius: 6px !important;
  padding: 10px 26px !important;
  position: relative;
  overflow: hidden;
  box-shadow:
    0 0 18px rgba(0, 212, 255, 0.45),
    0 0 4px rgba(255, 61, 0, 0.4),
    inset 0 1px 0 rgba(255, 255, 255, 0.2);
  transition: all 0.3s ease;
  text-shadow: 0 0 8px rgba(0, 0, 0, 0.55);
}
.stApp .stButton > button:hover,
.stApp .stDownloadButton > button:hover,
.stApp [data-testid="stFormSubmitButton"] button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 0 32px rgba(0, 212, 255, 0.78),
    0 0 12px rgba(255, 185, 56, 0.5),
    0 0 6px rgba(255, 61, 0, 0.65),
    inset 0 1px 0 rgba(255, 255, 255, 0.3);
  filter: brightness(1.1);
}
.stApp .stButton > button:active,
.stApp [data-testid="stFormSubmitButton"] button:active {
  transform: translateY(0);
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.3);
}

.ct-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 14px !important;
  border-radius: 999px !important;
  background: rgba(0, 212, 255, 0.08) !important;
  color: var(--arc-glow) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 600 !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.08em;
  border: 1px solid rgba(0, 212, 255, 0.35);
  box-shadow: 0 0 12px rgba(0, 212, 255, 0.25), inset 0 0 12px rgba(0, 212, 255, 0.1);
  text-transform: uppercase;
  margin-right: 8px;
}
.ct-pill::before {
  content: '◉';
  color: var(--arc-cyan);
  text-shadow: 0 0 8px var(--arc-cyan);
}

.stApp [data-testid="stProgress"] > div > div > div {
  background: linear-gradient(90deg, var(--strange-gold), var(--doom-fire), var(--arc-cyan)) !important;
  box-shadow: 0 0 16px rgba(255, 185, 56, 0.55);
  border-radius: 999px;
}
.stApp [data-testid="stProgress"] > div > div {
  background: rgba(5, 8, 24, 0.6) !important;
  border: 1px solid rgba(255, 185, 56, 0.25);
  border-radius: 999px;
}

.stApp [data-testid="stAlert"] {
  background: var(--bg-card) !important;
  color: var(--text-glow) !important;
  border-radius: 8px !important;
  backdrop-filter: blur(4px);
}
.stApp [data-testid="stAlertContentSuccess"] {
  border-left: 3px solid var(--arc-cyan) !important;
  box-shadow: 0 0 20px rgba(0, 212, 255, 0.2);
}
.stApp [data-testid="stAlertContentWarning"] {
  border-left: 3px solid var(--strange-gold) !important;
  box-shadow: 0 0 20px rgba(255, 185, 56, 0.2);
}
.stApp [data-testid="stAlertContentError"] {
  border-left: 3px solid var(--doom-fire) !important;
  box-shadow: 0 0 22px rgba(255, 61, 0, 0.3);
}
.stApp [data-testid="stAlertContentInfo"] {
  border-left: 3px solid var(--rune-violet) !important;
  box-shadow: 0 0 20px rgba(108, 47, 178, 0.25);
}

.stApp [data-testid="stMetric"] {
  background: var(--bg-card);
  border: 1px solid rgba(0, 212, 255, 0.2);
  border-radius: 8px;
  padding: 14px 18px;
  box-shadow: 0 0 20px rgba(108, 47, 178, 0.2);
}
.stApp [data-testid="stMetricLabel"] {
  color: var(--strange-gold) !important;
  font-family: 'Orbitron', sans-serif !important;
  font-size: 0.7rem !important;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}
.stApp [data-testid="stMetricValue"] {
  font-family: 'Orbitron', sans-serif !important;
  color: var(--arc-glow) !important;
  text-shadow: 0 0 12px rgba(0, 212, 255, 0.55);
}

.stApp [data-testid="stExpander"] {
  background: var(--bg-card) !important;
  border: 1px solid rgba(255, 185, 56, 0.2) !important;
  border-radius: 8px;
  box-shadow: 0 0 18px rgba(108, 47, 178, 0.15);
}
.stApp [data-testid="stExpander"] summary, .stApp [data-testid="stExpander"] p {
  color: var(--strange-gold) !important;
  font-family: 'Orbitron', sans-serif !important;
  letter-spacing: 0.08em;
}
.stApp [data-testid="stExpander"] .streamlit-expanderContent { color: var(--text-glow); }

.stApp pre, .stApp code {
  background: rgba(5, 8, 24, 0.85) !important;
  color: var(--arc-glow) !important;
  border: 1px solid rgba(0, 212, 255, 0.2);
  font-family: 'JetBrains Mono', monospace !important;
}

@keyframes rune-rotate { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes rune-rotate-rev { from { transform: rotate(360deg); } to { transform: rotate(0deg); } }
@keyframes arc-pulse {
  0%, 100% { filter: drop-shadow(0 0 8px var(--arc-cyan)); }
  50% { filter: drop-shadow(0 0 22px var(--arc-cyan)) drop-shadow(0 0 4px var(--strange-gold)); }
}

.cosmic-header {
  position: relative;
  padding: 18px 0 10px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 16px;
}
.cosmic-header .arc-reactor {
  width: 56px; height: 56px;
  animation: arc-pulse 3s ease-in-out infinite;
  flex-shrink: 0;
}
.cosmic-header .title-stack { flex-grow: 1; }
.cosmic-rune {
  position: absolute;
  top: -60px;
  right: -60px;
  width: 260px;
  height: 260px;
  opacity: 0.22;
  pointer-events: none;
  z-index: 0;
}
.cosmic-rune .ring-outer { animation: rune-rotate 60s linear infinite; transform-origin: center; }
.cosmic-rune .ring-inner { animation: rune-rotate-rev 40s linear infinite; transform-origin: center; }
.cosmic-line {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--arc-cyan), var(--strange-gold), var(--doom-fire), transparent);
  margin: 4px 0 18px 0;
  box-shadow: 0 0 8px rgba(0, 212, 255, 0.5);
}

.portal-frame {
  position: relative;
  margin: 60px auto 30px;
  width: 100%;
  max-width: 520px;
  text-align: center;
}
.portal-frame svg.portal-rune {
  width: 360px;
  height: 360px;
  display: block;
  margin: 0 auto;
  filter: drop-shadow(0 0 30px rgba(255, 185, 56, 0.7)) drop-shadow(0 0 60px rgba(255, 61, 0, 0.35));
}
.portal-frame svg.portal-rune .ring-outer { animation: rune-rotate 24s linear infinite; transform-origin: center; }
.portal-frame svg.portal-rune .ring-mid { animation: rune-rotate-rev 18s linear infinite; transform-origin: center; }
.portal-frame svg.portal-rune .ring-inner { animation: rune-rotate 12s linear infinite; transform-origin: center; }
.portal-frame .portal-title {
  font-family: 'Orbitron', sans-serif;
  font-weight: 700;
  letter-spacing: 0.32em;
  text-transform: uppercase;
  font-size: 1.2rem;
  color: var(--strange-gold);
  text-shadow: 0 0 14px var(--strange-gold), 0 0 30px rgba(255, 61, 0, 0.55);
  margin-top: -200px;
  position: relative;
  z-index: 1;
}
.portal-frame .portal-subtitle {
  font-family: 'Rajdhani', sans-serif;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--text-dim);
  font-size: 0.85rem;
  margin-top: 6px;
  margin-bottom: 180px;
}

#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; }
</style>
"""

_ARC_REACTOR_SVG = """
<svg class="arc-reactor" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="46" fill="none" stroke="#00d4ff" stroke-width="1" opacity="0.4"/>
  <circle cx="50" cy="50" r="38" fill="none" stroke="#00d4ff" stroke-width="0.8" opacity="0.5" stroke-dasharray="3 3"/>
  <circle cx="50" cy="50" r="28" fill="none" stroke="#00d4ff" stroke-width="1" opacity="0.6"/>
  <g stroke="#00d4ff" stroke-width="2" fill="none" opacity="0.8">
    <line x1="50" y1="14" x2="50" y2="28"/>
    <line x1="50" y1="72" x2="50" y2="86"/>
    <line x1="14" y1="50" x2="28" y2="50"/>
    <line x1="72" y1="50" x2="86" y2="50"/>
  </g>
  <circle cx="50" cy="50" r="14" fill="#00d4ff" opacity="0.25"/>
  <circle cx="50" cy="50" r="8" fill="#4be0ff"/>
  <circle cx="50" cy="50" r="3" fill="#ffffff"/>
</svg>
"""

_COSMIC_RUNE_SVG = """
<svg class="cosmic-rune" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
  <g class="ring-outer" fill="none" stroke="#ffb938" stroke-width="0.8">
    <circle cx="100" cy="100" r="92" stroke-dasharray="2 6"/>
    <path d="M 100 12 L 102 22 L 98 22 Z M 100 188 L 102 178 L 98 178 Z M 12 100 L 22 102 L 22 98 Z M 188 100 L 178 102 L 178 98 Z" fill="#ffb938"/>
  </g>
  <g class="ring-inner" fill="none" stroke="#c98d2a" stroke-width="0.7">
    <circle cx="100" cy="100" r="70" stroke-dasharray="3 4"/>
    <circle cx="100" cy="100" r="58"/>
    <path d="M 60 60 L 70 70 M 130 70 L 140 60 M 60 140 L 70 130 M 130 130 L 140 140" stroke-width="1"/>
  </g>
  <circle cx="100" cy="100" r="40" fill="none" stroke="#ffb938" stroke-width="0.5" stroke-dasharray="1 2"/>
</svg>
"""

_PORTAL_RUNE_SVG = """
<svg class="portal-rune" viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="portalGlow">
      <stop offset="0%" stop-color="#ff7a45" stop-opacity="0.4"/>
      <stop offset="40%" stop-color="#ffb938" stop-opacity="0.2"/>
      <stop offset="100%" stop-color="#ffb938" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <circle cx="150" cy="150" r="140" fill="url(#portalGlow)"/>
  <g class="ring-outer" fill="none" stroke="#ffb938" stroke-width="1.2">
    <circle cx="150" cy="150" r="135" stroke-dasharray="3 8"/>
    <g stroke-width="1.5">
      <path d="M 150 10 L 154 28 L 146 28 Z" fill="#ffb938"/>
      <path d="M 150 290 L 154 272 L 146 272 Z" fill="#ffb938"/>
      <path d="M 10 150 L 28 154 L 28 146 Z" fill="#ffb938"/>
      <path d="M 290 150 L 272 154 L 272 146 Z" fill="#ffb938"/>
    </g>
  </g>
  <g class="ring-mid" fill="none" stroke="#c98d2a" stroke-width="0.9">
    <circle cx="150" cy="150" r="108" stroke-dasharray="2 5"/>
    <circle cx="150" cy="150" r="92"/>
    <g stroke="#ffb938" stroke-width="1">
      <path d="M 78 78 L 90 90 M 210 90 L 222 78 M 78 222 L 90 210 M 210 210 L 222 222"/>
      <circle cx="150" cy="58" r="3" fill="#ffb938"/>
      <circle cx="150" cy="242" r="3" fill="#ffb938"/>
      <circle cx="58" cy="150" r="3" fill="#ffb938"/>
      <circle cx="242" cy="150" r="3" fill="#ffb938"/>
    </g>
  </g>
  <g class="ring-inner" fill="none" stroke="#ff7a45" stroke-width="0.8">
    <circle cx="150" cy="150" r="68" stroke-dasharray="1 3"/>
    <circle cx="150" cy="150" r="50"/>
    <path d="M 150 110 L 158 132 L 180 140 L 162 156 L 168 178 L 150 168 L 132 178 L 138 156 L 120 140 L 142 132 Z" fill="none" stroke="#ffb938" stroke-width="1"/>
  </g>
</svg>
"""

st.markdown(_THEME_CSS, unsafe_allow_html=True)

_HEADER_HTML = (
    '<div class="cosmic-header">'
    f"{_ARC_REACTOR_SVG}"
    '<div class="title-stack">'
    '<h1>CDP Generation</h1>'
    '<div class="cosmic-line"></div>'
    '</div>'
    f"{_COSMIC_RUNE_SVG}"
    '</div>'
)
st.markdown(_HEADER_HTML, unsafe_allow_html=True)
st.caption("Магия Calltouch CDP · уникальные сценарии под клиента из URL и брифа")


def _check_password() -> bool:
    """Простой пароль-gate. Пароль читается из st.secrets['app_password']
    (Streamlit Cloud) или из env STREAMLIT_PASSWORD (локальный/Render).
    Если ни то ни другое не задано — без auth (для локальной разработки)."""
    import os

    expected = None
    try:
        expected = st.secrets.get("app_password")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — secrets.toml может отсутствовать локально
        expected = None
    if not expected:
        expected = os.environ.get("STREAMLIT_PASSWORD")
    if not expected:
        return True

    if st.session_state.get("auth_ok"):
        return True

    portal_html = (
        '<div class="portal-frame">'
        f"{_PORTAL_RUNE_SVG}"
        '<div class="portal-title">Sanctum · Portal</div>'
        '<div class="portal-subtitle">Произнеси кодовое слово</div>'
        '</div>'
    )
    st.markdown(portal_html, unsafe_allow_html=True)

    _col_l, col_c, _col_r = st.columns([1, 2, 1])
    with col_c:
        pwd = st.text_input("Пароль", type="password", key="pwd_input", label_visibility="collapsed", placeholder="• • • • • • • •")
        if st.button("Открыть портал", type="primary", use_container_width=True):
            if pwd == expected:
                st.session_state["auth_ok"] = True
                st.rerun()
            else:
                st.error("Заклинание не сработало. Проверь пароль.")
    st.stop()


_check_password()

try:
    settings = get_settings()
except (ConfigError, ValueError) as exc:
    st.error(f"Ошибка конфигурации: {exc}")
    st.info("Проверь, что ANTHROPIC_API_KEY задан в окружении (Streamlit Secrets / .env).")
    st.stop()

# Технические детали моделей сознательно скрыты в UI — менеджер видит чистый портал.

def _normalize_url(raw: str) -> str:
    """Достроить https:// если пользователь ввёл просто `level.ru`."""
    raw = raw.strip().strip("/").lstrip("@")
    if not raw:
        return raw
    if raw.startswith(("http://", "https://")):
        return raw
    return f"https://{raw}"


with st.form("generation_form", clear_on_submit=False):
    col_url, col_count = st.columns([3, 1])
    with col_url:
        client_url = st.text_input(
            "URL клиента",
            placeholder="level.ru (можно без https://)",
            help="Главный домен сайта клиента. Префикс https:// добавится автоматически.",
        )
        additional_raw = st.text_input(
            "Дополнительные домены (через запятую, опционально)",
            placeholder="business.level.ru, srub-lw.ru",
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

    primary_url = _normalize_url(client_url)
    additional = [
        _normalize_url(u) for u in additional_raw.split(",") if u.strip()
    ]

    try:
        request = GenerationRequest(
            client_url=primary_url,  # type: ignore[arg-type]
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
