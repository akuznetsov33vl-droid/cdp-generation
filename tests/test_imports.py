"""Smoke-тест: проверяем, что все модули импортируются без ошибок."""

from __future__ import annotations


def test_all_modules_import() -> None:
    import src.config  # noqa: F401
    import src.exceptions  # noqa: F401
    import src.llm  # noqa: F401
    import src.models  # noqa: F401
    import src.orchestrator  # noqa: F401
    import src.prompts  # noqa: F401
    from src.agents import (  # noqa: F401
        data_scout,
        doc_keeper,
        pdf_renderer,
        reviewer,
        scenario_author,
        visual_designer,
    )


def test_prompts_exist() -> None:
    from src.prompts import load_prompt

    for name in ("data_scout_extract", "doc_keeper_brief", "scenario_author"):
        text = load_prompt(name)
        assert len(text) > 100, f"Промпт {name} подозрительно пуст"
